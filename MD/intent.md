# Intent

## Why we're building this
1. **To win, or place well, in Gnani.ai's Great Indian AI Internship Challenge**, and use it to get an internship.
2. **To show a real voice agent, not a demo script.** We already have a working call pipeline (from an earlier project) that was tuned on real calls. Rebuilding its speech layer on Gnani's models shows we can integrate new models into a production pipeline.
3. **To solve a real problem.** Kirana shops take orders by phone all day, often while serving customers at the counter. Calls get missed and orders get misheard.

## Two things on one line (DEC-027)
Dukaan Dost answers two kinds of call. A **customer** orders from the shop and can put it on credit. A **would-be or new shopkeeper** asks what loan they can get for a shop and what it will cost them each month, which comes from SIH 2026 problem statement PS 26091. The loan answers are computed by code, not guessed by the model, so each call has an exactly checkable result.

## The twist: a credit book by phone
Most regulars at a kirana buy on **udhaar** (credit) and settle at the month's end. Dukaan Dost also keeps that book: "likh lo" adds the order to their account, "kitna baaki hai?" gets the balance, "Saturday ko dunga" records the promise. No other visible entry does this (see [idea_research.md](idea_research.md), DEC-026).

## Who it's for
- **The shopkeeper:** they get a written order (items, quantities, prices, total) instead of scribbled notes, and don't miss calls during a rush.
- **The caller:** they order in whatever language they think in, including mixing Hindi or Telugu with English, the way people actually talk.
- **The judges:** a clear, measured demonstration of Prisma and Timbre on noisy, code-mixed phone audio.

## What "done" looks like
- A live call from a browser tab takes a Hinglish order end to end, handles one interruption, reads back the total and shows the order summary. That's the 60-second video.
- Telugu and Hindi calls work too.
- An evaluation table with **measured** STT word error rate, order accuracy and time to first audio, on clean and noisy audio.
- A README a judge can follow in five minutes.
- Submitted by **Nov 9, 2026**.

## What we're not trying to do
- Payments, inventory sync or a shop dashboard beyond a small order viewer.
- Multiple simultaneous calls (one call at a time).
- Replacing Gemini with Gnani's LLM: Evon isn't on the API.
