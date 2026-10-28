# Product requirements: Dukaan Dost

## Users
- **Caller:** a regular customer of the shop, ordering by phone in Telugu, Hindi, English or a mix.
- **Shopkeeper:** reads the order summary and packs the order.

## The call, step by step
1. **Greeting.** The agent answers within about a second of the call connecting, greets in the shop's name and offers the languages (see language selection below).
2. **Language.** The caller's language is set for the call. It can change if the caller clearly switches or asks to.
3. **Ordering.** The caller names items in any order and in any language. For each item the agent:
   - matches it to the stock list (Hindi and Telugu names count; so do common brand names like "Maggi" or "Amul butter")
   - asks for the quantity or pack size if it's missing or ambiguous ("1 kg or 5 kg?")
   - confirms the item, quantity and price before moving on
   - says so plainly if the shop doesn't stock it, and suggests the nearest item the shop does have. **It never invents an item or a price.**
4. **Changes.** The caller can remove or change an item ("make the atta 10 kg", "cancel the soap").
5. **Read-back.** When the caller is done, the agent reads back each item and the total **in words**, in the caller's language.
6. **Delivery and payment.** It confirms delivery or pickup and payment by UPI or cash on delivery, using the shop's (synthetic) details.
7. **Close.** It thanks the caller and says when to expect delivery.
8. **Summary.** At hang-up, the agent writes `orders/<call_id>.json` and `orders/<call_id>.txt`.

## Must handle
| Situation | Expected behaviour |
|---|---|
| Caller interrupts while the agent is speaking | The agent stops and listens (existing barge-in) |
| "Repeat that" | Replays the last reply (existing) |
| "Stop" / "chup" | Stops speaking (existing) |
| Item not in stock list | Says it's not available; offers the nearest match only if one exists |
| Ambiguous quantity | Asks; never guesses |
| Background noise or silence | No reply to noise; a short prompt after real silence (existing filters) |
| Caller switches language mid-call | Follows a clear switch (native-script detection), not one stray word |
| Caller hangs up mid-order | Writes a summary marked incomplete |

## Udhaar (credit) ledger (DEC-026)
Regulars buy on credit and settle at the month's end. The agent handles three things by phone:
| Caller says | Agent does |
|---|---|
| "Isko udhaar mein likh dena" / "khate mein daal do" (with their name) | Confirms the name against the shop's customer list, adds the order total to their balance, and reads back the new balance |
| "Mera kitna baaki hai?" / "నా బాకీ ఎంత?" | Reads out the outstanding balance in words, and the date of the last purchase |
| "Saturday ko de dunga" | Records the promise-to-pay date and confirms it back |

Rules:
- **Customers are identified by the name they say, matched against a synthetic customer list** in the knowledge files. No phone numbers or caller ID (rule R-2).
- **Unknown name:** the agent doesn't create a credit account. It says the shopkeeper will confirm, and marks the order "credit pending" in the summary.
- **A credit limit** per customer (e.g. ₹2,000). Over the limit, the agent politely says the shopkeeper has to approve.
- **Never shames or pressures** a caller about dues. A neutral, friendly tone.
- The order summary gains `payment: "udhaar"`, `customer`, `balance_before` and `balance_after`. A ledger file (`orders/ledger.json`) holds the running balances, plus a readable `ledger.txt`.

## Order summary format
`orders/<call_id>.json`:
```json
{
  "call_id": "20261101-153012",
  "language": "hi-IN",
  "status": "confirmed",
  "items": [
    {"sku": "ATTA-5KG", "name": "Aashirvaad Atta 5 kg", "qty": 1, "unit_price": 0, "line_total": 0}
  ],
  "total": 0,
  "delivery": "home delivery",
  "payment": "UPI",
  "transcript": [{"role": "caller", "text": "..."}, {"role": "agent", "text": "..."}]
}
```
(Prices are placeholders here. The real values come from `products_pricing.md`.)

`orders/<call_id>.txt` holds the same information as a readable bill, for the shopkeeper.

## Non-functional requirements
- **Time to first audio:** as low as we can make it. Measure it; don't promise a number before the eval.
- **Languages:** te-IN, hi-IN, en-IN, plus Hinglish.
- **Data:** synthetic only. No call recording during the contest.
- **Runs on:** a Raspberry Pi with one phone paired over Bluetooth.

## Out of scope
Payments, stock sync, multiple simultaneous calls, outbound calls, customer accounts.
