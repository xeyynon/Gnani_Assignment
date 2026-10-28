# Plan of action: everything that isn't model work

The model work (Prisma, Timbre, Gemini) is in [ml_model_integration.md](ml_model_integration.md). This file covers the rest: the shop, orders, evidence and outreach.

## 1. Repo hygiene (day 1)
- Move the upstream reference clone **out of** `E:\Projects\Gnani` (its folder name, git history and `companies/` contain client data). See [rules.md](rules.md) R-3.
- `git init`. Check `.gitignore` covers `local_config.py`, `.env`, `ai_caller.log*`, `logs/`, `orders/` (except `orders/samples/`), `eval/audio/`.
- Add `GNANI_API_KEY` and `GEMINI_API_KEY` to `local_config.example.py`.
- Add `gnani-vachana` and `websockets` to `requirements.txt` (pin the versions after the install works).
- Set `CALL_DATA_ENABLED` to default to `0` (DEC-007).

## 2. The shop: `companies/dukaan_dost/` (build step 7)
| File | Content |
|---|---|
| `config.yaml` | `system_prompt` for the order-taking persona: confirm each item and quantity, read the total back in words, never invent items or prices, ask when the quantity is unclear, keep replies to 1–2 short sentences. `fallback_messages` for `en-in`, `hi-in` and `te-in` |
| `knowledge/core/always_on.md` | Shop name, hours, languages, how ordering works, the rules for read-back |
| `knowledge/products_pricing.md` | ~60 synthetic items, **one `##` section per item or small group**, each with: English name, Hindi name (Devanagari and romanized), Telugu name (script and romanized), pack sizes, price per pack, a SKU |
| `knowledge/ordering_payment.md` | UPI (fake ID, e.g. `dukaandost@upi`) or cash on delivery; minimum order |
| `knowledge/delivery_shipping.md` | Delivery radius, timing, delivery charge |
| `knowledge/faq.md` | Open hours, returns of damaged goods, substitutions |
| `packaging.md`, `refund_policy.md`, `payment_issues.md`, `recommendations.md` | Short stubs (the retriever expects these file names) |

Item categories: rice, atta, dal (toor, moong, chana, urad), oil (sunflower, groundnut, mustard), sugar, salt, tea, coffee, milk, curd, paneer, Amul butter, bread, eggs, Maggi, biscuits, soap, detergent, toothpaste, spices (turmeric, chilli, coriander), onions, potatoes, tomatoes.

Use made-up shop names and IDs. Brand names (Amul, Maggi, Aashirvaad) are fine as product names, since that's how callers order, but **no real people, phone numbers or addresses**.

## 3. Order summary (build step 8)
- A per-call order state, held next to the conversation history and reset on the same call boundaries (`_clear_history`).
- At call end, write `orders/<call_id>.json` and `.txt`. `call_id` is a timestamp like `20261101-153012`.
- Check every line against the stock list before writing (the SKU exists and the price matches the knowledge file).
- Optional: a tiny web page (`orders/index.html` or a small Flask app) listing the orders, for the demo video.

## 3b. Udhaar ledger (DEC-026)
- `knowledge/customers.md` isn't one of the retriever's fixed file names, so the customer list goes in `knowledge/payment_issues.md` (a credit is a payment arrangement) or in `always_on.md` if it's short. Decide when building.
- `orders/ledger.json`: `{customer: {balance, credit_limit, last_purchase, promise_date, entries: [...]}}`, updated only after the order is confirmed; checked against the stock list like the order itself.
- In the demo: the order viewer shows the customer's balance before and after.

## 4. Evaluation assets (build step 9)
- 20 order scripts in `eval/scripts/*.json`: the expected items and quantities, plus the turns the caller says.
- Audio in `eval/audio/clean/` and `eval/audio/noisy/`. Noise from a royalty-free source (credit it in the README), mixed at ~10 dB SNR.
- An eval runner that plays each script through the pipeline offline (no Bluetooth) and logs WER, order match and time to first audio.

## 5. README (build step 10)
The problem; an architecture diagram; how Prisma and Timbre are used (Prisma v3.0 language detection, keyterms, `commit`; Timbre v3.0 voice); the results table (measured only); how to run; "all data is synthetic".

## 6. Videos and posts (Surya)
| When | What |
|---|---|
| By Nov 5 | LinkedIn and X posts with a short clip, tagging **Gnani AI**, #GreatIndianAIInternshipChallenge #GnaniAI |
| By Nov 8 | The 60-second demo: a real call, a Hinglish order, one interruption, the total read back, the summary on screen |
| By Nov 8 | The 2–3 minute walkthrough: architecture plus the results table |
| Nov 9 | The submission form |
