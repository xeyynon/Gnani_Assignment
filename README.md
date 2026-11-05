# Dukaan Dost

[![CI](https://github.com/xeyynon/Gnani_Assignment/actions/workflows/ci.yml/badge.svg)](https://github.com/xeyynon/Gnani_Assignment/actions/workflows/ci.yml)

A voice agent for a neighbourhood kirana store. A customer calls and orders in **Telugu, Hindi, English or Hinglish**. The agent matches each item to the shop's stock list, confirms quantities and prices, reads back the total, keeps the shop's **udhaar (credit) book**, gives small-business **loan guidance**, and writes an order summary the shopkeeper sees on a dashboard.

Built for Gnani.ai's **Great Indian AI Internship Challenge**, on Gnani's **Prisma** (speech to text) and **Timbre** (text to speech). Gnani has no public language model, so a separate one reads the order (Groq's gpt-oss by default, Gemini as an option).

It is software only: you call it from a browser tab. A phone-number transport (Twilio and Exotel media streams) is built and tested against a stand-in provider, but has not been run on a real phone network.

## The idea: the model never does the money
Language models are good at hearing "do kilo cheeni aur ek litre tel" and bad at arithmetic they must get exactly right. So the split is strict:

- the **model** only says which items and how many (one JSON note per turn),
- plain **code** checks every item against the stock list, rounds each line half-up, adds the total, decides credit limits, and **writes every sentence that states an amount**, in the caller's language, from templates.

What the customer hears is therefore exactly what the dashboard shows, and a model slip can add or drop an item but cannot invent a price or a total.

## How a call works
```
Caller (browser microphone, 16 kHz) ──WebSocket──▶ voice-activity detection (webrtcvad)
   ▶ Gnani Prisma v3.0, streaming speech to text (language detected per call)
   ▶ language model: one JSON order note (items, quantities, payment, name)
   ▶ order code: stock check, rounding, totals, credit limit, spoken sentences (en / hi / te)
   ▶ Gnani Timbre v3.0, streaming text to speech ──▶ back to the caller
   at hang-up ▶ orders/<shop>/order_<id>.json (and loan_<id>.json, ledger.json)  ▶ dashboards
```
- **Barge-in:** the caller can interrupt; the agent stops and listens, and remembers only what was actually heard.
- **Udhaar:** the caller says a name; code finds the customer, checks the limit and balance, and approves, refuses, or leaves it to the shopkeeper. The model never decides.
- **Loan guidance:** a keyword check starts loan mode; the model only reads the amount and whether it is the caller's own money or the project cost; code computes the scheme, the loan and the instalment and speaks them, marked as indicative.
- **Many shops, one agent:** the call link `/s/<shop>/` picks the shop; each shop has a PIN-protected dashboard at `/s/<shop>/dashboard` (orders, credit balances, loan enquiries), and one admin page looks after every shop.

How Gnani's models are used:
- **Prisma v3.0:** streaming WebSocket, language `indic-auto`, the shop's product names sent as boost terms, a commit after the caller stops.
- **Timbre v3.0:** streaming WebSocket, 16 kHz audio, one voice for all four languages; a spare connection is opened ahead of time to save about 0.3 s per sentence.

The full architecture is in [MD/architecture.md](MD/architecture.md).

## Results
<!-- RESULTS:BEGIN -->
Not filled in yet: every figure here comes from a saved run in [evaluation/results/](evaluation/results/), and none has been taken since the latest fixes.
<!-- RESULTS:END -->

How it is measured: scripted calls, with synthetic Timbre voices, are played into the **real** agent (voice detection, Prisma, the language model, the order code, Timbre) by a replay transport, with no browser. The scorer compares the saved order with the expected one (items and quantities exactly), and reports word error rate, time to first audio and cut-off counts. Steady synthetic noise can be mixed in at a chosen level. The method, the scripts and the scorer are in [evaluation/](evaluation/README.md).

## Honest limits
- All voices, shops, customers and orders are **synthetic**. No real caller has used it.
- The browser call page has been exercised by automated browser tests, not yet by a person with a microphone on a long call.
- One call at a time; a second caller hears "busy". The design for several callers is in [MD/architecture.md](MD/architecture.md).
- The phone transport has not met a real provider.
- The Hindi and Telugu product names and sentences were written by the assistant and need a native speaker's check.
- The loan scheme figures come from the challenge's problem statement and are indicative; they are not any bank's or government's current terms.
- The language model runs on a free tier with a daily token limit, which caps how often the evaluation can be repeated.

## Getting started
Setup, keys and run commands are in **[SETUP.md](SETUP.md)**. In short:
```bash
pip install -r requirements.txt
cp .env.example .env            # add GNANI_API_KEY and GROQ_API_KEY
python -m dukaan_dost           # then open the printed address and press Start call
python -m pytest                # offline tests
```

## Repository layout
```
dukaan_dost/   the agent: run with `python -m dukaan_dost`
shops/         one folder per shop (config.yaml, stock.json, customers.json, knowledge/), see shops/README.md
evaluation/    scripted calls, the runner and scorer; committed results
tests/         offline tests (tests/manual needs cloud credentials)
scripts/       changelog.mjs (builds and InBuls), the checks CI runs, a local CI copy
.github/       GitHub Actions: CI on every push, a release and image per build tag
MD/            architecture, flow, product and phone-line notes, and the build reports
```

## Documentation
The architecture, call flow, product notes and phone-line set-up are in [MD/](MD/); what has shipped is in [CHANGELOG.md](CHANGELOG.md).

## Data
**All data in this project is synthetic.** The stock list, prices, customers, shop details, UPI ID, order scripts and test audio are made up. No real phone numbers, IDs or recordings of real calls are used, and call recording is turned off.
