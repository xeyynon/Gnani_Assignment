# Running AI Caller

## Quick start (recommended — terminal)

**Always check nothing is already running first** — two instances answering the
same call simultaneously is the single most common real problem hit while
testing this project (it sounds like the bot talking over itself):

```bash
ps aux | grep ai_caller_final3
```

If that shows nothing, start it:

```bash
cd "/home/pi/ai-caller" && setsid nohup /usr/bin/python3 ai_caller_final3.py > /dev/null 2>&1 < /dev/null &
disown
```

Watch it live:

```bash
tail -f ai_caller.log
```

(`Ctrl+C` here only stops `tail` — the app keeps running in the background.)

**2026-08-18: this used to redirect to `/tmp/live_test.log` instead of `/dev/null`.**
Found and fixed after it turned out `/tmp` on this Pi is `tmpfs` — RAM-backed, not disk —
confirmed via `mount | grep tmp`, capped at 1.9GB out of the Pi's ~3.7GB total RAM. Every
line the app logs already goes to `ai_caller.log` in the project directory via a
`RotatingFileHandler` (5MB × 3 backups, bounded, on real disk) — the `/tmp` redirect was
capturing the exact same content a second time, with **no rotation at all**, growing
straight into RAM for as long as the process stayed up. A long-running session (exactly
the kind this command is meant to support) could genuinely fill that 1.9GB and start
failing writes, or add real memory pressure to the whole system. Switching to `/dev/null`
loses nothing worth keeping: the only thing that redirect could ever have caught was a
crash traceback before the app's own logging is configured, and a process backgrounded
this way (`setsid`, no terminal attached) had no one watching it at that exact moment
anyway — `ai_caller.log` already has everything from just after that point on, and it's
the one file this project already invested in keeping bounded.

Stop it cleanly:

```bash
pkill -f ai_caller_final3.py
```

Verified: shuts down in under a second, every time, regardless of what the
threads were doing (a hardened shutdown path guarantees this — see
`ai_caller_final3.py`'s `main()`).

### Why `setsid` and the `> file 2>&1 < /dev/null &` redirection

Running it plain (`python3 ai_caller_final3.py &`, or piping through `tee` for
live output) was tried during development and caused the process to receive an
unexpected shutdown signal from the terminal/shell itself in some session
configurations — not a bug in the app, but real enough to bite during testing.
`setsid` fully detaches the process from the controlling terminal session, so
nothing your shell does afterward (closing a tab, returning focus, etc.) can
signal it. Always use the exact command above, not a simplified version.

## Running from Thonny

Thonny is configured (see `~/.config/Thonny/configuration.ini`) to run scripts
through a separate virtual environment:

```
/home/pi/venvs/whisper-env/bin/python3
```

— left over from earlier offline-Whisper experimentation, not the system
Python (`/usr/bin/python3`) that the terminal method above uses. This venv now
has the same dependencies installed (`pip install -r requirements.txt` was run
against it), so Thonny's Run button works. If a `ModuleNotFoundError` shows up
again in Thonny after adding a new dependency to `requirements.txt`, re-run:

```bash
/home/pi/venvs/whisper-env/bin/python3 -m pip install -r "/home/pi/ai-caller/requirements.txt"
```

Thonny's Stop button / closing the window may not shut the process down as
cleanly as `pkill` does via the terminal method — prefer the terminal for
anything beyond quick interactive debugging.

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| Bot's voice sounds like two overlapping replies | Two instances running at once | `pkill -f ai_caller_final3.py`, confirm `ps aux \| grep ai_caller_final3` is empty, start exactly once |
| Started it, but it "shut down" seconds later on its own | Terminal/shell signal delivery issue (see `setsid` note above) | Use the exact command in Quick Start, not a simplified one |
| `ssh: connect to host ... port 22: Connection timed out` | The Pi's IP changed (DHCP) | Find the new IP on the Pi itself (`hostname -I` or router/network tooling), update `~/.ssh/config` |
| `ModuleNotFoundError: No module named 'sarvamai'` (or similar) when run from Thonny | Thonny's configured interpreter doesn't have the app's dependencies | See "Running from Thonny" above |
| Nothing happens after "Ready — waiting for a call" | Normal — it's idle until a Bluetooth call comes in | Make the test call |

## Verifying it's healthy

```bash
ps aux | grep ai_caller_final3      # exactly one process, not zero or two
tail -30 ai_caller.log              # should end with "Ready — waiting for a call."
```

See `README.md` for architecture, setup, configuration, and testing.
