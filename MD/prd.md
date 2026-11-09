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
8. **Summary.** At hang-up, the agent writes `orders/<shop>/order_<call_id>.json` and `orders/<shop>/order_<call_id>.txt`.

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

## Call types (DEC-027)
The agent decides in the first turn which of two things the caller wants, and says what it can do ("order de sakte hain, ya dukaan ke liye loan ke baare mein bata sakte hain"). A caller can switch mid-call. Everything in this file above this section is the **shop order** call. The **loan guidance** call is below.

## Udyami loan guidance (DEC-027, from SIH 2026 PS 26091)
A would-be or new shopkeeper says how much money they can put in and what business they want.

**Inputs (three slots, confirmed back one at a time):**
- **Margin money** the caller can put in, e.g. "ek lakh".
- **Business type**, e.g. kirana, dairy, textiles (stored, not used in the arithmetic).
- **Place** (village or town), stored for the summary.

**The arithmetic (deterministic, never done by the language model):**
- Project cost = margin money ÷ 0.10. Maximum loan = 90% of the project cost. Example: ₹1,00,000 margin money gives ₹10,00,000 project cost and a ₹9,00,000 loan.
- Project cost up to ₹1.40 lakh: **Micro Finance Scheme**, 6.5% a year, 3-year repayment including a 3-month moratorium, loan up to ₹1.25 lakh.
- Project cost above ₹1.40 lakh up to ₹50 lakh: **Term Loan Scheme**, 8% a year, 7-year repayment including a 6-month moratorium, loan up to ₹45 lakh.
- Above ₹50 lakh: not covered; the agent says so.
- The agent gives an **approximate monthly instalment**, computed in code from the scheme's rate and tenure after the moratorium. The exact formula is fixed in decisions.md when the calculator is built and is covered by unit tests.

**Rules:**
- The agent says these figures are **indicative** and the bank or agency confirms. It never promises approval.
- It reads every amount back in words and asks the caller to confirm before calculating.
- The numbers come from a calculator module, and the agent only speaks what the module returns.
- The call produces a summary the caller could take to the agency: inputs, scheme, project cost, loan, rate, tenure, instalment. Written to `orders/` like an order, as `loan_<call_id>.json` and `.txt`.
- Synthetic callers only; no real names, places or phone numbers (R-2).

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
- The order summary gains `payment: "udhaar"`, `customer`, `balance_before` and `balance_after`. A ledger file (`orders/<shop>/ledger.json`) holds the running balances, plus a readable `ledger.txt`.

## Order summary format
`orders/<shop>/order_<call_id>.json`:
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

`orders/<shop>/order_<call_id>.txt` holds the same information as a readable bill, for the shopkeeper.

## Non-functional requirements
- **Time to first audio:** as low as we can make it. Measure it; don't promise a number before the eval.
- **Languages:** te-IN, hi-IN, en-IN, plus Hinglish.
- **Data:** synthetic only. No call recording during the contest (see decisions.md DEC-007).
- **Runs on:** any laptop, as software only. The caller is a browser tab.

## Out of scope
Payments, stock sync, multiple simultaneous calls, outbound calls, customer accounts.
