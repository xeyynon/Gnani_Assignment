# Submission drafts: posts, demo script, walkthrough, form

**Written 2026-11-05.** Drafts for Surya to edit and publish. Nothing here may carry a number that is not in a saved run in `evaluation/results/` (rule R-5). Every `[RESULT: ...]` marker below is a blank that is filled from a named result file after that run is read, or the sentence is cut. Do not fill a marker from memory.

## What may be claimed today (no run needed)
These are facts about what was built, checkable in the repo:
- A voice agent for a neighbourhood kirana shop that takes orders in Telugu, Hindi, English and Hinglish.
- Built on Gnani **Prisma** (speech to text) and **Timbre** (text to speech), both through their streaming WebSocket APIs. A separate language model (Groq gpt-oss) reads the order; Gnani has no public one.
- **The model never does the money.** It only says which items and how many; code checks the stock list, rounds, adds and writes every amount that is spoken.
- Udhaar (credit) book with a limit check; loan guidance from computed figures; the shopkeeper dashboard; an admin dashboard.
- A scripted-caller evaluation harness with a scorer; all data synthetic.
- Software only: you call it from a browser tab.

## What may NOT be claimed until the fact exists
| Claim | Needs |
|---|---|
| Any accuracy, WER or latency figure | The named saved run (`orders_clean_fixes_20b`, `orders_noisy10db_120b`, ...) |
| "Works on a real phone call" or a phone number | A real provider call (B-39); today it is built against a stand-in only |
| "Tested with real people" | A real call or user test, written down |
| Telugu or Hindi wording is natural | A native speaker's check (B-16) |
| Loan figures are an official scheme's terms | The check of the problem statement (DEC-047); say "indicative figures from the problem statement" |

## LinkedIn post (draft)
> **I built a voice agent that takes a kirana shop's orders in Telugu, Hindi, English and Hinglish.**
>
> Small shops in India still run on phone calls: "do kilo atta, ek litre tel, aur Parle-G." Dukaan Dost answers those calls. It listens with **Gnani Prisma**, speaks with **Gnani Timbre**, and keeps the shop's udhaar (credit) book.
>
> The part I care about most: **the language model never touches the money.** It only works out which items and how many. Plain code checks the stock list, rounds, adds up the total and writes every amount the agent says, so what the customer hears is exactly what the shopkeeper's dashboard shows.
>
> What it does:
> - takes and changes orders by voice, in four languages
> - checks the stock list and says what is out of stock
> - approves or refuses udhaar against the customer's limit
> - gives small-business loan guidance from computed figures
> - gives the shopkeeper a dashboard of orders and balances
>
> How I tested it: [RESULT: one sentence from `orders_clean_fixes_20b` and `orders_noisy10db_120b`, e.g. how many scripted calls and the share of orders exactly right, with the date]. All voices, shops and customers are synthetic.
>
> Built for the @Gnani.ai Great Indian AI Internship Challenge.
> Demo video below. Code: [GitHub link]
>
> #GreatIndianAIInternshipChallenge #GnaniAI

## X post (draft, one post, with the video)
> I built Dukaan Dost: a voice agent that takes a kirana shop's orders in Telugu, Hindi, English and Hinglish, on @GnaniAI Prisma + Timbre.
>
> The model never does the money. Code checks stock, adds up, and speaks every amount.
>
> [RESULT: one measured number with what it counts]
>
> Demo + code: [link]
> #GreatIndianAIInternshipChallenge #GnaniAI

If the platform trims the tag, tag **Gnani AI** on LinkedIn and **@GnaniAI** on X (check the handle on the challenge page before posting).

## 60-second demo: shot list and spoken script
Record one real call in Chrome, headphones on, the shopkeeper dashboard open in a second window. Languages: Hinglish first, then one Telugu sentence. Use only the made-up shop. No real name, number or face on screen.

| Time | On screen | You say / the agent says |
|---|---|---|
| 0:00 to 0:05 | Title card: "Dukaan Dost: voice orders for a kirana shop" | (no voice) |
| 0:05 to 0:12 | Call page, press Start call; the agent greets | Agent greets in Hinglish |
| 0:12 to 0:25 | Order panel filling | You: "Do kilo cheeni aur ek litre tel chahiye." Agent confirms each item with its price and the running total |
| 0:25 to 0:33 | You interrupt mid-answer | You: "Nahi, cheeni teen kilo kar do." The agent stops, accepts the change |
| 0:33 to 0:42 | You say a Telugu sentence | You ask for one more item in Telugu; the agent answers in Telugu |
| 0:42 to 0:50 | "Bas itna hi" then udhaar | Agent reads the whole order and total back, asks how to pay; you: "Udhaar pe, Ramesh." Agent states the balance and the new balance |
| 0:50 to 0:58 | Dashboard: the order and the updated credit balance appear | Voice-over: "The shopkeeper sees the order and the balance. The model never did the arithmetic." |
| 0:58 to 1:00 | End card with the repo link and the tags | (no voice) |

Before recording: restart the server (`python -m dukaan_dost`), do one practice call, and check the order panel shows the lines. If the Telugu turn fails on the day, cut it; do not hide it.

## 2 to 3 minute walkthrough: outline
1. **The problem (20 s):** a shop owner on the phone all day; orders missed, credit kept in a notebook.
2. **The call path (40 s):** the diagram in the README: browser audio, voice detection, Prisma, the model's order note, the order code, Timbre. Say which parts are Gnani's.
3. **Why the model never does the money (30 s):** show one order where the spoken total equals the dashboard total.
4. **Udhaar and loans (30 s):** the limit check; a loan quote with "indicative".
5. **How it was tested (40 s):** the scripted callers, clean and noisy; the results table from the README, read as measured, with the limits (synthetic voices, one shop, small counts).
6. **What is not done (20 s):** no real phone number yet, one call at a time, wording to be checked by native speakers. Say it plainly.

## Submission form: answers to fill in
| Field | Draft |
|---|---|
| Title | Dukaan Dost: a multilingual voice agent for neighbourhood kirana shops |
| One-line problem | Small shops take orders and give credit by phone in Telugu, Hindi and Hinglish, and lose orders and track credit by hand |
| Target users | Kirana shop owners and their regular customers, including small-town shops |
| Gnani models used | Prisma v3.0 (streaming speech to text, language detected per call), Timbre v3.0 (streaming text to speech, one voice for all four languages) |
| Other models | Groq gpt-oss for the order note (Gnani has none public); Gemini is wired in as an option |
| What is novel | Money and quantities are decided by code, not by the model; the model only extracts; every spoken amount is generated from templates |
| Results | [RESULT: the table from the README, same numbers] |
| Links | GitHub repo; LinkedIn post; X post; demo video; walkthrough |
| Honest limits | Synthetic voices and data; one call at a time; no live phone number; native-speaker check of Hindi and Telugu wording [status on the day] |
| Tier 2/3 question | Open (tasks.md): Surya checks whether the college or town counts |
