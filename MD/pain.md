# Pain

## The shop's pain (what we're solving)
- **Missed calls at rush hour.** The shopkeeper is serving the counter when the phone rings. Every missed call is a lost order, often to the next shop.
- **Misheard orders.** "Do kilo" vs "dus kilo", "toor" vs "chana". Orders taken over a noisy line, from memory, go wrong, and fixing them costs a second delivery trip.
- **No written record.** Orders end up on scraps of paper or nowhere, so disputes ("I ordered 5 kg, not 1") have no answer.
- **Language.** Callers mix Hindi or Telugu with English mid-sentence. Most IVRs force "press 1 for English" and then fail anyway.
- **IVRs feel robotic.** Customers hang up on menus. A conversation that confirms each item feels like talking to the shop.

## Our pain (risks to delivery)
| Pain | Why it hurts | Mitigation |
|---|---|---|
| Tight deadline (15 days) | Gnani integration, shop data, eval, videos and posts all have to land | Smoke test first; cut the optional web page if time runs short |
| New, sparsely documented APIs | Prisma's end-of-segment behaviour isn't documented; Timbre is one request per connection | Smoke test; ask on Discord; keep Sarvam and Google as fallbacks |
| 5,000 credits | The eval and testing can burn through them | Measure the cost per call early; keep the eval sized to fit |
| Gnani account limits | Possibly one active request at a time (B-07) | Check on app.gnani.ai first; one STT session per call as the fallback |
| Browser microphone audio | Cleaner than a phone line, so results can look better than a real call | Evaluate on simulated phone-line audio (8 kHz, µ-law, added noise) and say so |
| Echo and interruptions | The agent can hear itself without headphones | Browser echo cancellation is on; tune with measurements (transport_plan.md) |
| Engagement-based shortlisting | A good build with no reach may not get seen | Posts by Nov 5 with a real clip |
