# Help from Smart Caller (the upstream project)

Dukaan Dost is built on **Smart Caller**, Surya's Raspberry Pi phone agent. An earlier version ran for a private business (a client, which isn't named anywhere in this repo, see [rules.md](rules.md) R-3).

## What we checked on 2026-10-26
We cloned the upstream GitHub repo (latest commit `a69a3bf`, 2026-08-19) and compared it file by file with this folder, ignoring line endings.

**Result: the code in this folder is the upstream code at that latest commit, with the client removed.** Every difference is de-identification:
- `COMPANY_DIR` was hardcoded to the client's folder; here it comes from the `COMPANY_NAME` env var and fails loudly if that's unset.
- The greeting used the client's name; here it uses `{COMPANY_NAME}`.
- The validator's greeting regex named the client; here it's generic.
- Code comments that named the client's products now say "product" or "deployment".
- Paths under the client's Pi user became `/home/pi/...`.
- `benchmark_dataset.json`, the README, RUNNING.md, the deploy files and the tests were scrubbed the same way.

**So no code port is needed.** The latest upstream fixes (the Aug 17 latency work and the Aug 19 barge-in, STT-bias and repeat fixes) are already here.

## What was left out on purpose
| Upstream item | Why it's not here |
|---|---|
| Git history | Contains the client's name and paths |
| The client's `companies/<client>/` folder | Client prompt and knowledge base |
| `HANDOFF.md` | Names the client and its infrastructure. **Its lessons are in these MD files** (decisions, bugs, tried-and-failed) |
| `benchmarks/archive/` | Results on the client's question set |

## What we reuse
| Piece | Notes |
|---|---|
| The whole call pipeline (`ai_caller_final3.py`) | Six threads, VAD, barge-in, call generations, language lock, filters |
| The provider dispatch pattern | `stt_provider.py`; we copy it for `tts_provider.py` |
| `stt_sarvam.py` | The reference for `stt_gnani.py`: thread plus asyncio, `is_stale`, semaphore |
| `tts_google.py` | The reference for `tts_gnani.py`: streaming class, `failed`, locks |
| `conversation_manager.py`, `knowledge_retriever.py`, `validator.py` | Unchanged; the shop goes in `companies/dukaan_dost/` |
| The benchmark harness | Extended for order accuracy |
| The deploy scripts and the systemd unit | Paths may need adjusting |
| The lessons | [decisions.md](decisions.md), [failmlmodel.md](failmlmodel.md), [tried_and_failed.md](tried_and_failed.md), [tried_and_implemented.md](tried_and_implemented.md), [bugs.md](bugs.md) |

## Upstream measurements: context only, never results
Upstream measured these on real calls with Sarvam STT and Google TTS:
- span from end of speech to first audio of 1.2–2.5 s per turn on a busy ~3-minute call (concurrency fix)
- the unexplained gap in time to first audio dropped from 300–1,000 ms to 6–531 ms (Aug 17 change)

They show the pipeline is fast enough to be worth building on. **They aren't Dukaan Dost numbers and must not appear in the README or the submission** (R-5).
