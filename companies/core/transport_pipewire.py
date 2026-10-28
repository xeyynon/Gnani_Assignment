"""
transport_pipewire.py

The original transport: a phone paired to a Raspberry Pi over Bluetooth
HFP/SCO, with the Pi capturing and playing the call through PipeWire
(pw-record / pw-play). Moved here from ai_caller_final3.py unchanged in
behaviour (DEC-029), so the pipeline can run on other transports and the
Pi stays available for comparison.

Linux only: needs wpctl, pw-link, pw-record, pw-play and bluetoothctl.
"""

import logging
import os
import re
import select
import subprocess
import threading
import time

from .transport import Capture, PlaybackTimeout, Transport

log = logging.getLogger("transport.pipewire")


def _open_diag_log(env_name: str, what: str):
    """An opt-in stderr capture file (never a PIPE: nothing would read it)."""
    path = os.environ.get(env_name)
    if not path:
        return None
    try:
        return open(path, "ab", buffering=0)
    except OSError as e:
        log.warning(f"[DIAG] Could not open {what} stderr log: {e}")
        return None


class PipewireCapture(Capture):
    def __init__(self, proc):
        self._proc = proc

    def read_frame(self, size: int, timeout_sec: float) -> bytes:
        """
        Reads exactly `size` bytes from pw-record's stdout, bounded by
        `timeout_sec`. A plain blocking .read() has no timeout, so if
        pw-record ever stalled mid-call without closing its pipe the
        recorder would hang forever. Returns fewer than `size` bytes
        (possibly empty) on timeout or EOF, which the recorder treats as
        a stream to reopen.
        """
        proc = self._proc
        buf = bytearray()
        deadline = time.time() + timeout_sec
        while len(buf) < size:
            remaining = deadline - time.time()
            if remaining <= 0:
                return bytes(buf)
            ready, _, _ = select.select([proc.stdout], [], [], remaining)
            if not ready:
                return bytes(buf)
            chunk = os.read(proc.stdout.fileno(), size - len(buf))
            if not chunk:
                return bytes(buf)
            buf += chunk
        return bytes(buf)

    def close(self) -> None:
        proc = self._proc
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


class PipewireTransport(Transport):
    name = "pipewire"
    sample_rate = 16000
    # Bluetooth HFP echoes the agent's own voice back, and the SCO link adds delay.
    default_echo_tail_sec = 1.2
    needs_echo_link_guard = True

    def __init__(self):
        self._play_lock = threading.Lock()
        self._play_proc = None
        # pw-record's stderr normally leaves no trace, so SCO packet
        # loss, resampler xruns and node errors are invisible. Set
        # AI_CALLER_PW_STDERR=<path> to capture it; the same for
        # AI_CALLER_PW_PLAY_STDERR on the playback side.
        self._rec_err = _open_diag_log("AI_CALLER_PW_STDERR", "pw-record")
        self._play_err = _open_diag_log("AI_CALLER_PW_PLAY_STDERR", "pw-play")

    # -- call detection ---------------------------------------------------

    def find_nodes(self):
        try:
            out = subprocess.run(
                ["wpctl", "status"], capture_output=True, text=True, timeout=5
            ).stdout
            i = re.search(r"(bluez_input\.[0-9A-Fa-f_]+\.\d+)", out)
            o = re.search(r"(bluez_output\.[0-9A-Fa-f_]+\.\d+)", out)
            return (i.group(1) if i else None, o.group(1) if o else None)
        except Exception:
            return None, None

    def device_name(self) -> str:
        try:
            out = subprocess.run(
                ["bluetoothctl", "devices", "Connected"],
                capture_output=True, text=True, timeout=5
            ).stdout
            names = [" ".join(l.split()[2:]) for l in out.splitlines() if len(l.split()) > 2]
            return ", ".join(names) or "unknown"
        except Exception:
            return "unknown"

    def cut_echo_links(self) -> None:
        """
        WirePlumber treats the Bluetooth HFP link as a normal "phone call
        through your laptop" device and auto-routes it through the Pi's
        onboard ALSA output ("mailbox") for local monitoring, which
        creates a loop: bluez_input (caller's incoming voice) -> onboard
        speaker -> onboard speaker's monitor port -> bluez_output (back
        out to the caller), so the caller hears their own voice echoed
        back. We never want that pass-through (only our own
        pw-record/pw-play talking to the bluez nodes directly), so every
        poll we find and cut any alsa_output<->bluez link.
        """
        try:
            out = subprocess.run(
                ["pw-link", "-l"], capture_output=True, text=True, timeout=5
            ).stdout
        except Exception:
            return

        current = None
        for line in out.splitlines():
            m = re.match(r"\s*\|(->|<-)\s*(.+)$", line)
            if m is None:
                current = line.strip()
                continue
            if current is None:
                continue
            arrow, other = m.group(1), m.group(2).strip()

            # "|->" means current is the output/source, other is the input/dest.
            # "|<-" means the reverse: other is the source, current is the dest.
            src, dst = (current, other) if arrow == "->" else (other, current)

            if ("alsa_output" in src and "bluez_" in dst) or \
               ("alsa_output" in dst and "bluez_" in src):
                try:
                    subprocess.run(
                        ["pw-link", "-d", src, dst],
                        capture_output=True, timeout=5
                    )
                    # DEBUG, not INFO: fires in bursts of 4-8 lines at
                    # every call boundary.
                    log.debug(f"[AUDIO] Cut loopback link: {src} -> {dst}")
                except Exception as e:
                    log.debug(f"[AUDIO] Failed to cut link {src} -> {dst}: {e}")

    # -- audio in / out ---------------------------------------------------

    def open_capture(self, node: str) -> Capture:
        proc = subprocess.Popen(
            ["pw-record", "--target", node, "-",
             "--rate", str(self.sample_rate), "--channels", "1", "--format", "s16"],
            stdout=subprocess.PIPE,
            stderr=(self._rec_err or subprocess.DEVNULL),
        )
        return PipewireCapture(proc)

    def play(self, node: str, wav_bytes: bytes, timeout_sec: float) -> None:
        # Popen + communicate() instead of subprocess.run(): run() gives
        # no handle, so an in-flight reply could not be stopped at hangup
        # and kept streaming into the next call (the Bluetooth OUTPUT
        # node id is stable across calls, so that audio really does reach
        # the next caller).
        proc = subprocess.Popen(
            ["pw-play", "--target", node, "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=(self._play_err or subprocess.DEVNULL),
        )
        with self._play_lock:
            self._play_proc = proc
        try:
            proc.communicate(input=wav_bytes, timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            # A stalled Bluetooth link would otherwise block this call
            # forever, silently ending all further replies for the call.
            proc.kill()
            proc.communicate()
            raise PlaybackTimeout(f"pw-play did not finish within {timeout_sec}s")
        finally:
            with self._play_lock:
                self._play_proc = None

    def stop_playback(self) -> bool:
        with self._play_lock:
            proc = self._play_proc
        if proc is not None and proc.poll() is None:
            proc.kill()
            return True
        return False
