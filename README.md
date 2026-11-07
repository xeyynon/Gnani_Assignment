# Dukaan Dost

[![CI](https://github.com/xeyynon/Gnani_Assignment/actions/workflows/ci.yml/badge.svg)](https://github.com/xeyynon/Gnani_Assignment/actions/workflows/ci.yml)

A voice agent for a neighbourhood kirana store. A customer calls and orders in **Telugu, Hindi, English or Hinglish**. The agent matches each item to the shop's stock list, confirms quantities and prices, reads back the total, keeps the shop's **udhaar (credit) book**, gives small-business **loan guidance**, and writes an order summary the shopkeeper sees on a dashboard.

Built for Gnani.ai's **Great Indian AI Internship Challenge**, on Gnani's **Prisma** (speech to text) and **Timbre** (text to speech). Gnani has no public language model, so a separate one reads the order (Groq's gpt-oss by default, Gemini as an option).

It is software only: you call it from a browser tab, or from an ordinary phone through a provider's number. The phone transport (Twilio and Exotel media streams) was tested against a stand-in provider and then took two real calls on an Exotel trial number on 2026-11-07; it is a demonstration line, not a production one.

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
- **Prisma v3.0:** streaming WebSocket, the shop's product names sent as boost terms, a commit after the caller stops. The first turn of a call lets Prisma choose the language (`indic-auto`); from the second turn of a Hindi or Telugu call the language is named, and a turn that comes back empty is heard again with the language named, because Prisma's own choice is unreliable on short answers (measured below).
- **Timbre v3.0:** streaming WebSocket, 16 kHz audio, one voice for all four languages; a spare connection is opened ahead of time to save about 0.3 s per sentence.

The full architecture is in [MD/architecture.md](MD/architecture.md).

## Results
<!-- RESULTS:BEGIN -->
Every figure below comes from a saved run in [evaluation/results/](evaluation/results/). Voices are synthetic Timbre voices, not people.

**Prisma on its own, no language model** ([stt_accuracy_prisma](evaluation/results/stt_accuracy_prisma.md), 2026-11-07): the 65 turns of the order script, each sent four ways. "Exactly right" means word for word against the script (number words turned into digits). The phone line is my own simulation (8 kHz, 300 to 3,400 Hz, mu-law), not a real operator's audio.

| Way of sending | Turns exactly right (of 65) | Turns heard as nothing |
|---|---|---|
| Clean audio, Prisma chooses the language | 25 | 3 |
| Clean audio, language named | 31 | 0 |
| Simulated phone line, Prisma chooses | 16 | 10 |
| Simulated phone line, language named | 19 | 3 |

Short turns (up to 1.6 s: "cash", "that's all", a name) were exactly right on 14 of 31 with Prisma choosing and 19 of 31 with the language named; Telugu calls on 5 of 16 and 10 of 16. This is why the agent now names the language.

**Scripted credit and loan calls, the whole pipeline** ([credit_loans_clean_120b](evaluation/results/credit_loans_clean_120b.md), 2026-11-06, gpt-oss-120b): 4 of 4 order calls and 4 of 4 loan calls exactly right, every turn answered (18 of 18), first audio 2.5 s at the median and 3.4 s at the 90th percentile after the caller's last word. Only 8 calls, so the 95% interval is wide (51% to 100%), and it was scored against the shop's stock before the loose-atta item was added.

**Not available yet:** a valid score for the 20-call order script. Two full runs (gpt-oss-20b and gpt-oss-120b) were marked INVALID because the model's daily token limit ran out near their end, so no figure from them is quoted; they are kept as evidence in `evaluation/results/INVALID_*`. A valid run is planned for when the model's daily window clears.

**Seen, not scored:** on 2026-11-07 two real phone calls to an Exotel trial number connected to the agent and were heard; one saved an order (1 litre of oil, cash, confirmed).
<!-- RESULTS:END -->

How it is measured: scripted calls, with synthetic Timbre voices, are played into the **real** agent (voice detection, Prisma, the language model, the order code, Timbre) by a replay transport, with no browser. The scorer compares the saved order with the expected one (items and quantities exactly), and reports word error rate, time to first audio and cut-off counts. Steady synthetic noise can be mixed in at a chosen level. The method, the scripts and the scorer are in [evaluation/](evaluation/README.md).

## Honest limits
- All voices, shops, customers and orders are **synthetic**. No real caller has used it.
- The browser call page has been exercised by automated browser tests, not yet by a person with a microphone on a long call. Two real phone calls have been made by one person, who was also the developer.
- One call at a time; a second caller hears "busy". The design for several callers is in [MD/architecture.md](MD/architecture.md).
- The phone line runs on an Exotel trial number through a temporary tunnel, with no KYC-approved production number; the phone-line figures above use a simulated line, not real operator audio.
- Prisma still mishears short answers and numbers ("ek litre" was written as "8 litre" even on clean audio); the code asks again or moves the order on, but the first hearing can be wrong.
- No valid score exists yet for the whole 20-call order script (see Results).
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
MD/            project documentation, start at MD/DukaanDost_MASTER.md
```

## Documentation
All project docs live in [MD/](MD/). Start with [MD/DukaanDost_MASTER.md](MD/DukaanDost_MASTER.md). How builds and internal changes are numbered is in [MD/project_docs_guide.md](MD/project_docs_guide.md); what has shipped is in [CHANGELOG.md](CHANGELOG.md).

## Data
**All data in this project is synthetic.** The stock list, prices, customers, shop details, UPI ID, order scripts and test audio are made up. No real phone numbers, IDs or recordings of real calls are used, and call recording is turned off.
