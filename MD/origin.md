# Origin of the call pipeline

Dukaan Dost's call pipeline (voice activity detection, interruption handling,
the per-call language lock, call isolation, and the streaming hand-offs between
speech-to-text, the language model and text-to-speech) was first built in an
earlier voice-agent project by the same author. That project ran on a
Raspberry Pi with a Bluetooth-paired phone and was tuned on real calls between
July and August 2026. This repository starts from that code with everything
specific to its first customer removed (the customer is never named here, see
[rules.md](rules.md) R-3), and is renamed and restructured for Dukaan Dost.

## What we reuse
| Piece | Notes |
|---|---|
| The call pipeline (`dukaan_dost/app.py`) | Six threads, VAD, barge-in, call generations, language lock, filters |
| The provider dispatch pattern | `stt_provider.py`; copied for `tts_provider.py` |
| `stt_sarvam.py` | The reference for `stt_gnani.py`: thread plus asyncio, `is_stale`, semaphore |
| `tts_google.py` | The reference for `tts_gnani.py`: streaming class, `failed`, locks |
| `conversation_manager.py`, `knowledge_retriever.py`, `validator.py` | Used as they are; the shop goes in `shops/dukaan_dost/` |
| The benchmark harness | In `evaluation/`; extended for order and loan accuracy |
| The Pi deploy scripts and systemd unit | In `deploy/` |
| The lessons | [decisions.md](decisions.md), [failmlmodel.md](failmlmodel.md), [tried_and_failed.md](tried_and_failed.md), [tried_and_implemented.md](tried_and_implemented.md), [bugs.md](bugs.md) |

## What was left behind on purpose
| Item | Why |
|---|---|
| The earlier project's git history | Contains customer details |
| Its shop content (prompt, knowledge base) | Customer material |
| Its benchmark results | Measured on the customer's question set |
| Its Google-STT diagnostic tool | Specific to an investigation that is closed (see [failmlmodel.md](failmlmodel.md)); still in this repo's git history |

## Measurements from the earlier project: context only, never results
The earlier project measured these on real calls with Sarvam STT and Google TTS:
- end of speech to first audio of 1.2–2.5 s per turn on a busy ~3-minute call (after the concurrency fix)
- an unexplained gap in time to first audio that dropped from 300–1,000 ms to 6–531 ms (the 2026-08-17 change)

They show the pipeline is fast enough to build on. **They aren't Dukaan Dost numbers and must not appear in the README or the submission** (R-5).

## What changed when it became Dukaan Dost (2026-10-28, InBul10)
- `ai_caller_final3.py` became the `dukaan_dost/` package (`python -m dukaan_dost`), and `companies/` became `shops/`.
- The benchmark tools moved to `evaluation/`; the two live cloud tests moved to `tests/manual/`.
- Environment variables were renamed: `COMPANY_NAME` is now `SHOP_NAME` (default `dukaan_dost`) and the `AI_CALLER_*` diagnostics are `DUKAAN_*`.
- The log file is `dukaan_dost.log`; the service is `dukaan-dost.service`.
