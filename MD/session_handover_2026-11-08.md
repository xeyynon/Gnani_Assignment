# Hand-over: 2026-11-08 (early morning)

Read [DukaanDost_MASTER.md](DukaanDost_MASTER.md) for the status, [poa_nov5_to_9.md](poa_nov5_to_9.md) for the plan and [phone_setup.md](phone_setup.md) for the phone line. This note says what happened on Nov 7, what is proven and what is next.

## What changed
- **Build 1016** (`a439851`): the fixes from the first two real phone calls (B-87 to B-94, listed in [bugfixed.md](bugfixed.md)): the call's language is named to Prisma from the second turn (narrowed to Telugu only on Nov 8, B-96, after a Telugu loan call was decoded as Hindi); an empty turn is heard again with the language named; a rate limit on one gpt-oss model falls back to the other; every call leaves a counts-only record that the dashboard data carries; a silent no-change turn asks what comes next; a shorter greeting; the demo shop sells atta loose by the kilo and in 5 and 10 kg bags.
- **Build 1014** (B-86, every call after the first was deaf) was made for one fix; the batching rule says to wait for about ten. Build 1016 is the first batch made under that rule.
- **The phone line works end to end**: an Exotel trial number, a Voicebot applet, a Cloudflare quick tunnel and the telephony transport. Two real calls from a phone connected, were heard and saved an order (`orders/dukaan_dost/order_20261107-215910-717`).

## What is proven, and how
- 1,225 offline tests pass.
- Prisma alone, 65 synthetic turns, four ways ([results](../evaluation/results/stt_accuracy_prisma.md)): on a simulated phone line 16 turns were exactly right against 25 clean and 10 were empty against 3; with the language named, Telugu calls were exactly right on 10 of 16 turns against 5 of 16.
- `credit_loans_clean_120b`: 8 of 8, rerun on 2026-11-08 against the new stock and Build 1019 (first audio 2.2 s median, 3.6 s at the 90th percentile). An intermediate run with Hindi also named to Prisma lost one Telugu loan call (3 of 4 loans, `credit_loans_hindi_named_120b`, B-96): Build 1019 names only Telugu.

## What is not proven
- **No valid full-call score exists after the fixes.** Both Groq models' daily budgets are used by the evaluation runs of Nov 6 and 7 (`INVALID_orders_clean_20b`, `INVALID_orders_clean_search_120b`: a full 20-call run needs about a whole day of a model's 200,000 tokens). The 20b model's window clears about 20:40 on Nov 8, the 120b model's depends on tonight's use.
- The language change (B-94) and the retry (B-93) are untested on a real call; the phone line in the evaluation is my own simulation, not Exotel's audio, and the voices are synthetic.
- The shop's new atta item names in Hindi and Telugu need a native-speaker check (B-16).

## What is running
- The agent on port 8766 with `AUDIO_TRANSPORT=telephony`, `ORDER_CATALOGUE=search` and the 120b model; a Cloudflare quick tunnel whose address changes whenever it restarts (the Exotel applet URL must be updated each time).
- The Exotel flow "Dukaan Dost Voice Agent" is attached to the trial number 09513886363. The token is in the applet URL.

## Next, in order
1. A third real call, in Hindi and in Telugu if possible, to see whether short answers are heard now.
2. A valid full-call evaluation: search mode on gpt-oss-20b from about 20:40 on Nov 8, nothing else on that model meanwhile. Fill the README results block only from a valid run.
3. The dashboard panel for the call records (`calls` in the data feed): the UI session.
4. Decide the phone line for the demo by Nov 8 evening: Exotel's own note says full streaming needs KYC, but the trial number connected.
5. Surya: the demo video, the posts, the form, the native-speaker check, the loan figures.
