# Going Raspberry Pi-free: what to change and what to tune

**Written 2026-10-28.** Surya wants the agent to run without the Raspberry Pi and Bluetooth phone. This file says what is actually tied to the Pi, what the alternatives are, and which parts of the pipeline need re-tuning. The decision on which transport to build first is DEC-029: browser first, phone number as stretch. Section 7 step 1 (the interface) is done (InBul09).

## 1. What is tied to the Pi
I searched `dukaan_dost/app.py` (3,400 lines). The Pi-specific code is a small, bounded part:

| What | Where | Pi-specific because |
|---|---|---|
| Call start/end detection | `watchdog_thread` (line ~1069), `_find_nodes` (~931) | Polls `wpctl status` for Bluetooth audio nodes |
| Echo loopback cutting | `loopback_guard_thread` (~1155), `_kill_loopback_links` (~943) | PipeWire links between the onboard speaker and Bluetooth |
| Playing audio | `_play` (~1898), `_stop_playback` (~1955), `_play_greeting` (~1968) | Spawns `pw-play --target <bluez node>` |
| Capturing audio | `recorder_thread` (~2067) and its `pw-record` reader (~2011–2140) | Spawns one persistent `pw-record` per call |
| TTS fallback | ~1715 | `espeak-ng` |
| Echo handling in the logic | `ECHO_TAIL_SEC` (1.2 s), mic mute while playing, the barge-in gap windows | Built for Bluetooth HFP echo and SCO latency |

**Not Pi-specific, and kept as is:** `processor_thread` (filters, language lock, the LLM turn, reply checks, streaming TTS), the STT/TTS/LLM modules, `conversation_manager`, `knowledge_retriever`, `validator`, the loan calculator. These are most of the code and nearly all of the logic.

## 2. What replaces the phone and the Pi
There are three ways to take audio in and send audio out. They are not exclusive.

| Option | What it is | Cost / effort | Real phone call? | Risks |
|---|---|---|---|---|
| **A. Browser or laptop** | A web page captures the mic over a WebSocket (16 kHz PCM) and plays the agent's audio. Or a plain laptop mic and speaker for development | Free; a few days | **No** (it is the same kind of demo most public entries show) | Loses the "answers a real phone call" edge; Noise Canceller award needs *telephone* audio |
| **B. Cloud phone number** | A provider (Exotel, Plivo, Twilio, Telnyx, or LiveKit SIP) gives a number and streams the call's audio to our server over a WebSocket (typically 8 kHz mu-law) | Paid or trial credit; KYC and regulatory paperwork for Indian numbers; needs a public URL (a tunnel) | **Yes** | Time: the paperwork and approval can take days we don't have; I could not verify which providers give a trial Indian number (see section 6) |
| **C. Both, behind one interface** | A transport interface with browser and phone implementations; the browser one first | Medium | Yes, once B works | Slightly more work up front, but every later step is cheaper |

**Recommendation: C, starting with A.** A gives us a working Pi-free build in days and is also the best place to tune. B is attempted in parallel as the stretch goal for the demo. If B's paperwork stalls, the entry still stands on A, with the telephone-audio claims made only about what we actually tested (see 5).

Gnani documents **LiveKit** and **Pipecat** plugins (`livekit-plugins-gnani`, `pipecat-gnani`, the latter tested with Pipecat 1.5.0), but neither page covers telephony. Moving the whole agent onto one of those frameworks would throw away our tuned barge-in, language lock and call isolation, so I would **not** rewrite on them. They are worth knowing about if a provider offers a ready-made bridge to one of them.

## 3. The seam: a transport interface
Replace the five Pi-specific pieces with one small interface, so the thread logic stays as it is:

```
class Transport:
    def wait_for_call()      -> blocks until a call starts; returns a call id
    def call_active()        -> bool                       (replaces the wpctl polling)
    def open_capture()       -> object with read(nbytes, timeout) -> bytes   (replaces pw-record)
    def play(wav_bytes)      -> blocks; interruptible        (replaces pw-play)
    def stop_playback()      -> None
    sample_rate: int         # 16000 (browser/PCM) or 8000 (telephony)
    echo_tail_sec: float     # 0 where the far end already cancels echo
```
Implementations: `PipewireTransport` (today's code, kept so we can compare), `WebSocketTransport` (browser; later telephony), `LocalAudioTransport` (laptop mic and speaker, for development).

## 4. What to re-tune
Every number below was tuned on a Bluetooth line (DEC-009 to DEC-018). They are not wrong, but they are **the wrong baseline** for a clean network audio stream. Re-tune against measurements from the evaluation harness, not by feel.

| Setting | Today (Bluetooth) | Why it may change | How to decide |
|---|---|---|---|
| `ECHO_TAIL_SEC` 1.2 s, mic muted while the agent speaks | Bluetooth echo and SCO delay | A browser (with echo cancellation on) or a phone network doesn't echo the agent back into the mic. This is the **biggest** gain: it allows true speak-over barge-in instead of listening only between sentences | Set to 0 on the new transports; test with the agent talking and the caller interrupting |
| `BARGE_IN_*` thresholds (energy, margin, pitch) | Built to tell echo from the caller | Mostly unnecessary if there is no echo; keep the pitch check as a safeguard | Count false interruptions in a recorded test |
| `VAD_HANGOVER_MS` 650 | Chosen to stop natural pauses splitting an utterance (DEC-010) | Clean audio may allow less, which is a direct latency saving | Sweep 350–650 ms against time to first audio and fragment rate |
| `VAD_ENERGY_THRESHOLD` 180, `VAD_MODE` 2 | Bluetooth noise floor | Different gain and noise floor | Re-measure |
| `SAMPLE_RATE` 16000 | Bluetooth HFP wideband | Telephony is 8 kHz. webrtcvad supports 8 kHz, and Prisma accepts 8 kHz (64 ms frames of 1,024 bytes). Timbre can output mu-law at 8 kHz directly. Don't upsample then downsample | Pick the rate per transport; keep one internal rate per call |
| Prisma VAD headers | Defaults | Our own VAD already decides the end of speech and sends `commit` (DEC-023); the server-side VAD should not second-guess it. Telephony guidance: `x-vad-threshold` 0.65–0.75 | Tune in the smoke test |
| Greeting delay `GREETING_DELAY_SEC` 1.0 | Waiting for the Bluetooth link to settle | Not needed | Set to 0 |
| Concurrency (one STT session per utterance) | Was fine with Sarvam's high limit | Unknown for Gnani (B-07) | Check the account limit |
| Where it runs | Pi, 3.7 GB RAM | A laptop or a small cloud VM has plenty; **latency now includes the network hop to the user** | Log time from end of speech to first audio per transport |

## 5. What the Pi-free build gives up, and how to stay honest
- **Without a real call, don't claim one.** The README and the posts say "browser call" or "simulated phone line" unless a real number is wired up and tested (rule R-5).
- **Noise Canceller wants noisy *telephone* audio.** Gnani's own example for that award is a call summariser "tested on synthetic calls", so synthetic is acceptable. Our evaluation can degrade clean speech to a phone line (8 kHz, mu-law, added noise at ~10 dB SNR) and say exactly that.
- **The demo video** can still show a phone call if option B works; otherwise it shows the browser, clearly.
- **Keep the Pi transport.** It is the only one that has handled real calls so far; removing it would lose the comparison.

## 6. Open questions (unverified)
- Which provider gives a **trial or free Indian number** without a long approval, and whether it needs KYC for an individual. The research found: Twilio needs an approved regulatory bundle to buy a number, and a vendor page says Plivo and Exotel originate Indian calls while Twilio does not; one developer guide lists a roughly ₹500-a-month Indian number. These come from vendor and blog pages and **are not verified**.
- Whether a provider's media stream gives 8 kHz mu-law (expected) and how its barge-in signal works.
- Whether `webrtcvad` installs on Windows. It isn't installed on this machine; the `webrtcvad-wheels` package is said to provide Windows builds. To check.

## 7. Plan, in order
1. **Transport interface** with the Pipewire implementation moved behind it, behaviour unchanged. Prove it on the Pi if possible; otherwise by tests with a fake transport.
2. **`LocalAudioTransport`** (laptop mic and speaker), so the whole pipeline runs and is tuned on a laptop.
3. **`WebSocketTransport`** and a tiny web page: the browser "call".
4. Re-tune per section 4 using the evaluation harness; record each change as a decision.
5. **Stretch:** a telephony provider on the same WebSocket transport.

## Sources
- Gnani LiveKit plugin: https://docs.gnani.ai/livekit/introduction.md
- Gnani Pipecat plugin: https://docs.gnani.ai/pipecat/introduction.md
- Twilio India regulatory guidelines: https://www.twilio.com/en-us/guidelines/in/regulatory
- LiveKit SIP trunk setup: https://docs.livekit.io/telephony/start/sip-trunk-setup/
- Telnyx with LiveKit: https://developers.telnyx.com/docs/livekit/telephony.md
- Indian numbers for voice agents (blog, unverified): https://dev.to/animesh_gupta_705a19fc6f8/how-to-give-your-livekit-vapi-or-retell-voice-agent-a-real-indian-91-phone-number-am6
- Plivo with LiveKit (vendor page, unverified): https://www.plivo.com/livekit/
