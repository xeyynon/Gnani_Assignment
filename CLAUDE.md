# Dukaan Dost

A voice agent for a neighbourhood kirana shop, built for Gnani.ai's Great Indian AI
Internship Challenge on Gnani's Prisma (speech-to-text) and Timbre (text-to-speech), with
Gemini for reasoning. It answers calls in Telugu, Hindi, English and Hinglish, takes shop
orders (with an udhaar credit book), and gives loan guidance from computed figures.

**Deadline: Nov 10, 2026, 11:59 PM IST. Aim to submit Nov 9; social posts by Nov 5.**

## Read first
1. `MD/DukaanDost_MASTER.md`: status and the map of every doc.
2. `MD/tasks.md`: the checklist. `MD/decisions.md`: why things are the way they are.
3. `MD/rules.md` and `MD/agents.md`: how to work here.
4. The newest `MD/session_handover_*.md`.

## Layout
```
dukaan_dost/   the agent (`python -m dukaan_dost`); app.py is the main process
shops/         one folder per shop: config.yaml + knowledge/ (file names are fixed)
evaluation/    benchmarks and accuracy tools; results/ is committed
tests/         offline tests; tests/manual needs real cloud credentials
deploy/        Raspberry Pi install and run guides
scripts/       changelog.mjs
MD/            project documentation
```

## Commands
```bash
python -m pytest                         # offline tests (run before every commit)
python -m dukaan_dost                    # run the agent, from the project root
node scripts/changelog.mjs --next-internal
```

## Hard rules (full list in MD/rules.md)
- **Never commit keys.** `local_config.py` and `.env` stay gitignored.
- **Synthetic data only**: no real phone numbers, IDs or recorded calls. Call recording stays off.
- **No customer material from earlier work**: no names, prompts, knowledge bases or benchmark
  data. The customer is never named anywhere in this repo.
- **No unmeasured numbers** in the README, videos or submission. Every figure comes from a saved
  run in `evaluation/results/`.
- **Verify vendor facts against the live docs** (docs.gnani.ai); MD/external_research.md was
  read on 2026-10-28 and can go stale.
- **Model output is untrusted**: money (loan figures, order totals) is computed in code and the
  model only speaks it.
- Commit or push only when Surya asks.

## Versioning
User-visible changes ship as numbered **builds** (`build-N` tag, report in `MD/builds/`);
everything else (docs, tests, scripts, refactors) is an **InBul** (`InBulNN:` commit title).
Batch about 10 fixes per build. Never put "(Build N)" in a title and never hand-edit
`CHANGELOG.md`. The full flow is in `MD/project_docs_guide.md`.

## Architecture in one breath
Audio comes in through a `Transport` (`AUDIO_TRANSPORT`; Pi/Bluetooth today, browser next),
through webrtcvad endpointing, to a streaming STT provider (`STT_PROVIDER`), to Gemini with the
shop's knowledge, to a streaming TTS provider, and back out. Providers sit behind fixed
interfaces (`MD/integration_handoff.md`). Threads communicate only through queues and events,
and every queued item carries the call generation so nothing leaks between calls.
