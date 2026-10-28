# Running Dukaan Dost on the Raspberry Pi

This is for the Pi and Bluetooth-phone setup (`AUDIO_TRANSPORT=pipewire`, the
default). Setting a Pi up from scratch is in [INSTALL.md](INSTALL.md).

## Start

**Check nothing is already running first.** Two instances answering the same
call is the most common real problem (it sounds like the bot talking over
itself):

```bash
ps aux | grep dukaan_dost
```

If that shows nothing, from the project root:

```bash
setsid nohup .venv/bin/python3 -m dukaan_dost > /dev/null 2>&1 < /dev/null &
disown
tail -f dukaan_dost.log        # Ctrl+C stops only `tail`, not the app
```

Use exactly this form. Running it plain (`... &`, or piped through `tee`) let
the shell send the process a shutdown signal in some setups; `setsid` detaches
it from the terminal session entirely.

The output goes to `/dev/null` on purpose: `/tmp` on the Pi is RAM-backed, and
the app already writes a size-capped, rotating `dukaan_dost.log` on disk.

## Stop

```bash
pkill -f dukaan_dost
```

It shuts down in under a second, whatever the threads were doing.

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| The bot's voice sounds like two overlapping replies | Two instances running | `pkill -f dukaan_dost`, confirm `ps aux \| grep dukaan_dost` is empty, start once |
| It "shut down" seconds after starting | Terminal signal delivery | Use the exact command above |
| `ssh: connect to host ... Connection timed out` | The Pi's IP changed (DHCP) | Find the new IP on the Pi (`hostname -I`) and update `~/.ssh/config` |
| `ModuleNotFoundError` | Dependencies not installed in the interpreter you used | Use the project's `.venv`, and `pip install -r requirements.txt` |
| Nothing happens after "Ready — waiting for a call" | Normal: it's idle until a Bluetooth call comes in | Make a test call |

## Check it's healthy

```bash
ps aux | grep dukaan_dost      # exactly one process
tail -30 dukaan_dost.log       # ends with "Ready — waiting for a call."
```

See [../SETUP.md](../SETUP.md) for keys and configuration.
