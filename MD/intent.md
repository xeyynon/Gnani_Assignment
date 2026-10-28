# Intent

## Why we're building this
1. **To win, or place well, in Gnani.ai's Great Indian AI Internship Challenge**, and use it to get an internship.
2. **To show a real voice agent, not a demo script.** We already have a working phone agent (Smart Caller) that has handled real calls on a Raspberry Pi. Rebuilding its speech layer on Gnani's models shows we can integrate new models into a production pipeline.
3. **To solve a real problem.** Kirana shops take orders by phone all day, often while serving customers at the counter. Calls get missed and orders get misheard.

## Who it's for
- **The shopkeeper:** they get a written order (items, quantities, prices, total) instead of scribbled notes, and don't miss calls during a rush.
- **The caller:** they order in whatever language they think in, including mixing Hindi or Telugu with English, the way people actually talk.
- **The judges:** a clear, measured demonstration of Prisma and Timbre on noisy, code-mixed phone audio.

## What "done" looks like
- A real phone call to the Pi takes a Hinglish order end to end, handles one interruption, reads back the total and shows the order summary. That's the 60-second video.
- Telugu and Hindi calls work too.
- An evaluation table with **measured** STT word error rate, order accuracy and time to first audio, on clean and noisy audio.
- A README a judge can follow in five minutes.
- Submitted by **Nov 9, 2026**.

## What we're not trying to do
- Payments, inventory sync or a shop dashboard beyond a small order viewer.
- Multiple simultaneous calls (one phone, one Pi, one call).
- Replacing Gemini with Gnani's LLM: Evon isn't on the API.
