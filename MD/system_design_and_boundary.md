# System design and boundaries

## In scope
- One call at a time, from a browser tab on the same machine (or behind TLS).
- Telugu, Hindi, English and Hinglish.
- Taking an order against a fixed, synthetic stock list.
- Writing an order summary per call.
- An offline evaluation harness.

## Out of scope
- A real phone number or telephone line. A provider-backed transport could be added later (see [transport_plan.md](transport_plan.md)).
- Payments (we only *say* the UPI ID or "cash on delivery").
- Stock levels and live inventory.
- Multiple lines or simultaneous calls. A second browser is told the line is busy.
- Outbound calls.
- Recording calls (turned off for the contest, see [decisions.md](decisions.md) DEC-007).

## Where data goes
| Data | Leaves this machine to | Kept on this machine |
|---|---|---|
| Caller audio | Gnani Prisma (WSS) | Not stored (`CALL_DATA_ENABLED=0`) |
| Transcript and history | Google Gemini | `dukaan_dost.log` (gitignored, rotated) |
| Reply text | Gnani Timbre (WSS) | `dukaan_dost.log` |
| Order | — | `orders/` (gitignored, except synthetic samples) |
| API keys | Sent as headers to their own vendor only | `local_config.py` (gitignored) |

## Trust boundaries
- **Caller speech is untrusted input.** A caller can say "ignore your instructions". The system prompt and the validator keep the agent on ordering, and prices come only from the knowledge files, never from the caller.
- **Model output is untrusted until validated.** `validator.py` strips banned patterns. Any order JSON from the LLM must be checked against the stock list (SKU exists, price matches) before it's written.
- **Vendor APIs can fail.** Every network call has a timeout and a spoken fallback. STT failure plays an apology; TTS failure falls back to eSpeak today (English only; a Google TTS failover for Gnani is a possible addition); LLM failure plays `fallback_messages[lang]`.

## Model output versus code
The language model never does arithmetic that the caller will act on. Loan figures come from `loan_calculator.py`; order totals will come from code over the stock list. The model only speaks what code returns, and everything it says about money is checked against it.

## Limits we design around
| Limit | Source | Effect |
|---|---|---|
| Prisma v3.0 detects the language from a hint list (v2.5 needs one fixed language) | Gnani docs, 2026-10-28 | Send `hi-IN,en-IN,te-IN`; follow `detected_language_code` (DEC-023) |
| Prisma wants exactly 1,024-byte frames at real-time pace | Gnani docs | `feed()` regroups frames; don't burst-send |
| Prisma sessions are capped at 15 minutes | Gnani docs | A long call needs a reconnect. Calls are short, but guard it anyway |
| Timbre handles one request per connection at a time | Gnani docs | Serialise synthesis per connection, or keep a small pool |
| Timbre normalises numbers itself, but `auto` reads Latin-only text as English, and Telugu coverage is still being refined | Gnani docs, 2026-10-28 | Pass the language explicitly; thin pre-pass for units (DEC-024) |
| The account may allow only one active request; the concurrent-session cap is per organisation | Gnani docs, 2026-10-28 | Check on app.gnani.ai; fall back to one STT session per call (B-07) |
| 5,000 free credits | Gnani registration | Budget the eval; see [problem_statement-gap-plan.md](problem_statement-gap-plan.md) |
| The browser microphone runs at 44.1 or 48 kHz | Browser | The call page resamples to 16 kHz mono before sending |
