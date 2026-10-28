# Rules

Hard rules. If one has to break, stop and ask Surya first.

## Data and secrets
- **R-1 · Never commit keys.** `local_config.py` and `.env` stay gitignored. Keys go in headers to their own vendor only, never in logs, URLs or docs.
- **R-2 · Synthetic data only.** No real phone numbers, Aadhaar, PAN, addresses, or recordings of real calls. That covers the stock list, eval scripts, sample orders and screenshots. The contest disqualifies otherwise.
- **R-3 · No client material.** Nothing from the client-work folders on this machine and no client names, knowledge base, prompts, benchmark data or git history from the upstream deployment. The upstream reference clone **must not sit inside this repo**; keep it outside `E:\Projects\Gnani` and don't name it in committed files.
- **R-4 · Call recording stays off** (`CALL_DATA_ENABLED=0`) for this project.

## Honesty
- **R-5 · No unmeasured numbers.** Every figure in the README, videos, posts or submission comes from an eval run that's saved in the repo. Upstream measurements (from a different deployment and provider) can't be quoted as Dukaan Dost results.
- **R-6 · Engagement is genuine.** No bought likes, no engagement swaps.

## Code
- **R-7 · Keep the interfaces.** New backends match the contracts in [integration_handoff.md](integration_handoff.md); the main file imports only from the dispatchers.
- **Match the surrounding code**: comment density, naming, env-var knobs, locks around lazy singletons, and `gen != _call_gen` checks for anything queued.
- **Don't retune settled values** (hangover 650 ms, onset 2 frames, barge-in thresholds) without new evidence from a real call. See [decisions.md](decisions.md).
- **Test the number normaliser** with unit tests before the demo.

## Versioning and commits
- **R-8 · Build or InBul.** A change a user would notice on a call or in the order output is a **build**. Everything else (docs, MD updates, scripts, tests, eval figures) is an **InBul**. See [project_docs_guide.md](project_docs_guide.md) for the full flow.
- **R-9 · Never put "(Build N)" in a commit title.** The tag `build-N` is the source of truth. Never renumber or move a tag.
- **R-10 · Batch builds.** Wait for about 10 fixes, then make one build. That includes a single urgent fix.
- **R-11 · Don't hand-edit `CHANGELOG.md`.** `scripts/changelog.mjs` generates it. The hand-written part of a build report is written once and never overwritten.
- Commits carry only Surya's name, with no co-author trailers.
- Update the matching `MD/` file in the same commit as the change.
- Commit only when Surya asks; push (with tags) only when told "push".
