# Session handover: 2026-10-28

## Done this session
| Id | What |
|---|---|
| **Build 1000** (tag `build-1000`) | `git init` on `main`. The baseline commit: the inherited agent, already de-identified (DEC-020). Report: [builds/build-1000.md](builds/build-1000.md) |
| **InBul01** (tag `InBul01`) | Versioning and docs: `scripts/changelog.mjs`, [project_docs_guide.md](project_docs_guide.md), [frontend.md](frontend.md), the root `README.md` (now the Dukaan Dost front page) and `SETUP.md`, `DEC-NNN` ids in [decisions.md](decisions.md), the bug sections in [bugs.md](bugs.md), the `[ ] [/] [x] [~]` marks in [tasks.md](tasks.md), the pipeline agents in [agents.md](agents.md) |

## How versioning works now
- User-visible changes are **builds**: `--pending`, commit, `--tag`, which gives the tag `build-N`, a report and a CHANGELOG entry.
- Everything else is an **InBul**: commit `InBulNN: …`, then `--tag`.
- Full flow: [project_docs_guide.md](project_docs_guide.md). Rules R-8 to R-11 in [rules.md](rules.md).

## Verified
- `--pending` wrote `build-1000.md` and `CHANGELOG.md`; a second run kept the hand-written part and refreshed the file list.
- `--tag` checked that the commit title matches the report, then tagged `build-1000`. It refuses to tag a commit twice.
- No committed file contains the client's name (checked with `git grep --cached`).

## Not done, or blocked
- **Moving the upstream clone out of the folder failed** (permission denied; something may have a file open in it, e.g. VS Code). It's excluded through `.git/info/exclude` meanwhile (DEC-021). Close anything using it, then move the folder to `E:\Projects\upstream-ref\` and delete its line from `.git/info/exclude`.
- **CLAUDE.md is untracked** (also in `.git/info/exclude`) until the client name is out of it (DEC-022).
- Nothing pushed. There's no remote yet.

## Next
1. Rework CLAUDE.md (without the client name), then commit it as an InBul.
2. Build step 1: Gnani and Gemini keys in the example config and key loading, the new requirements, `CALL_DATA_ENABLED=0` by default, B-01. These are user-visible, so batch them into the next build.
3. Build step 2: the smoke test (an InBul), once the Gnani key exists.

## Later the same day: research (InBul02)
Re-read Gnani's live docs, the contest page, PyPI and Google's Gemini pages. The full record is in [external_research.md](external_research.md). What changed the plan:
- **Prisma v3.0** (released 2026-10-22) detects the language, has a `codemix` format, takes up to 200 `x-keyterms`, and has a `commit` frame to end an utterance immediately. Adopted as DEC-023; [ml_model_integration.md](ml_model_integration.md) is rewritten around it.
- **Timbre normalises numbers, ₹ and units itself.** We only keep a thin pre-pass (DEC-024).
- **New Gemini keys may not get `gemini-2.5-flash`** (B-06, DEC-025).
- **Risk B-07:** Gnani accounts can be limited to one active request. Check on app.gnani.ai first thing after registering.
- **Contest:** ten awards (Jugaad Genius and Crowd Favourite are worth a try too); the demo post must be a video of the working app and be live before submitting; engagement is counted at the cutoff.

Still unknown until the key exists: our concurrency limit, the credit cost per minute, Timbre's idle timeout, and whether `hi-en` works on v3.0 voices.

## Restructure for GitHub (InBul10)
Everything named for the earlier project was renamed before the first push (DEC-030): the `dukaan_dost/` package (`python -m dukaan_dost`), `shops/`, `evaluation/`, `tests/manual/`, a rewritten CLAUDE.md, new `.gitignore`/`.gitattributes`/`pytest.ini`. 76 offline tests pass. Still open before pushing: the cloned reference folder inside the project can't be moved (permission denied; it is untracked and excluded locally, but close whatever has it open and move it out), a `LICENSE` choice, and whether to rewrite the early commit titles that still name the earlier project.

## Software only (Build 1002)
The Raspberry Pi and Bluetooth are removed (DEC-032). `python -m dukaan_dost` serves a call page; a browser tab is the caller. New: `transport_websocket.py`, `web/index.html`, 21 new tests (87 in total). Removed: `transport_pipewire.py`, `deploy/`. The default speech providers still need keys (Sarvam STT and Google TTS credentials) until the Gnani backends exist, so a full call cannot run yet without them. Open: try the page in a real browser (B-08), possible gaps between sentence clips (B-09).

## Dashboards (Build 1003)
Surya asked for an admin dashboard and a shopkeeper dashboard. Chosen (DEC-034): shopkeeper first, the call link picks the shop, one admin password plus a PIN per shop. Built: shop registry, PIN sign-in with lock-out, the order/loan/ledger file format, demo data, the per-call shop in the agent, and the shopkeeper dashboard, checked in headless Chrome at desktop and phone widths. 219 Python tests and 20 Node tests pass. Not built: the agent writing real orders (so the dashboard shows demo data, B-11), and the whole admin dashboard. A screenshot check caught a real bug the tests missed (the page could not fetch its data when opened with the PIN in the URL, and sat on "Loading...").
