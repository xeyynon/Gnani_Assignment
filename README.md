# Dukaan Dost

[![CI](https://github.com/xeyynon/Gnani_Assignment/actions/workflows/ci.yml/badge.svg)](https://github.com/xeyynon/Gnani_Assignment/actions/workflows/ci.yml)

A phone-order voice agent for a neighbourhood kirana store. A customer calls the agent and orders in **Telugu, Hindi, English or Hinglish**. The agent matches each item to the shop's stock list, confirms quantities and prices, reads back the total in words, and writes an order summary for the shopkeeper.

Built for Gnani.ai's **Great Indian AI Internship Challenge**, on Gnani's **Prisma** (speech-to-text) and **Timbre** (text-to-speech) models, with Gemini for reasoning.

> **Status: in development.** The call pipeline works (built in an earlier project, see [MD/origin.md](MD/origin.md)) and now runs entirely in software: you place a test call from a browser tab. A real phone number is a later option, not built. The Gnani integration, the shop's stock list, order summaries and the evaluation are being built now. See [CHANGELOG.md](CHANGELOG.md) for what's shipped.

## How it works
```
Caller ──browser microphone──▶ WebSocket (16 kHz mono)
   ▶ voice activity detection (webrtcvad) ▶ Gnani Prisma, streaming STT
   ▶ Gemini, streamed, grounded in the shop's stock list ▶ Gnani Timbre, streaming TTS
   ▶ back to the caller's browser
   at hang-up ▶ orders/<shop>/order_<call_id>.json and .txt
```
- **Barge-in:** the caller can interrupt; the agent stops and listens.
- **Languages:** the call's language is locked once it's clear, and follows a real switch (for example, the caller starts speaking Telugu script).
- **Call isolation:** nothing from one call can leak into the next.
- **Many shops, one agent:** the call link `/s/<shop>/` picks the shop; each shop's owner has a PIN-protected dashboard at `/s/<shop>/dashboard` showing orders, credit balances and loan enquiries (demo data only until the agent writes real orders).

The full architecture is in [MD/architecture.md](MD/architecture.md).

## Getting started
Setup, keys and run commands are in **[SETUP.md](SETUP.md)**.

## Repository layout
```
dukaan_dost/   the agent: run with `python -m dukaan_dost`
shops/         one folder per shop (config.yaml + knowledge/), see shops/README.md
evaluation/    benchmark and accuracy tools; committed results
tests/         offline tests (tests/manual needs cloud credentials)
scripts/       changelog.mjs (builds and InBuls), and the checks CI runs
.github/       GitHub Actions: CI on every push, a release and image per build tag
MD/            architecture, flow, product and phone-line notes, and the build reports
```

## Documentation
All project docs live in [MD/](MD/). Start with [MD/DukaanDost_MASTER.md](MD/DukaanDost_MASTER.md). How builds and internal changes are numbered is in [MD/project_docs_guide.md](MD/project_docs_guide.md).

## Results
Coming from the evaluation run (STT word error rate, order accuracy and time to first audio, on clean and noisy audio). No figure appears here until it's measured.

## Data
**All data in this project is synthetic.** The stock list, prices, shop details, UPI ID, order scripts and test audio are made up. No real phone numbers, IDs or recordings of real calls are used, and call recording is turned off.
