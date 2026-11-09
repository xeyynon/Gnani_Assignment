# End-to-end test conversations

Written 2026-11-09 for whoever tests the phone line or the browser call by hand, and as the plain-words companion of [evaluation/scripts/e2e_phone.json](../evaluation/scripts/e2e_phone.json), which plays the same kind of conversations with synthetic voices. Prices come from `shops/dukaan_dost/stock.json` and credit limits from `shops/dukaan_dost/customers.json`; they are made up, like everything in the demo shop.

## Before you start
1. **Start the stack:** `python scripts/phone_demo.py` in a terminal (agent in phone mode and the tunnel), copy the printed address into the Exotel Voicebot applet, add your token after `token=` and Save ([phone_setup.md](phone_setup.md)). For the browser, open `http://127.0.0.1:8766/s/dukaan_dost/` and press Start call.
2. **Watch the agent's lines** (the terminal, or `dukaan_dost.log`): `[PHONE]` when a call connects, `Caller (<language>)` for what was heard, `[ORDER]` when the call ends and the order is saved.
3. **Credit balances move.** Scenarios P09 to P12 change or read the credit book. To start from the opening balances, stop the agent and delete `orders/dukaan_dost/ledger.json` (it is rebuilt from `customers.json`); make a copy first if you want to keep it.
4. **Speak naturally, one idea at a time, and leave a short pause** after each reply. Phone at your ear, quiet room. The agent hears one short word less reliably than a sentence ("cash" is the weak one).

How to read a row: **Say** is what you say, turn by turn. **The agent should** is the gist, with the amounts the code speaks. **Saved** is the order file (and the dashboard) after you hang up.

## A. Orders
| ID | Language | Say | The agent should | Saved |
|---|---|---|---|---|
| P01 | Hinglish | 1. "Do kilo atta aur ek litre tel, bas itna hi" 2. "Cash" 3. "Thank you" | After 1: read back 2 kilo loose atta 110 and 1 litre sunflower oil 165, total 275, and ask how to pay. After 2: "Thank you, your order is noted" and the delivery time. After 3: only a short thanks, **not** the whole order read again | 2 items, 275, cash, confirmed |
| P02 | Telugu | 1. "రెండు కిలోల బియ్యం, ఒక లీటర్ నూనె కావాలి" 2. "అంతే" 3. "యూపీఐ" | Telugu replies; 2 kilo rice 120 and 1 litre oil 165, total 285; asks payment; closes | 285, UPI |
| P03 | Hindi | 1. "एक किलो चीनी और दो पैकेट मैगी चाहिए" 2. "बस इतना ही" 3. "यूपीआई" 4. "धन्यवाद" | Hindi replies; sugar 44 and 2 Maggi 28, total 72; closes; a short thanks at the end | 72, UPI |
| P04 | English | 1. "Three kilos of rice and one kilo of toor dal" 2. "Make the rice two kilos" 3. "Remove the dal" 4. "That is all" 5. "UPI" | After 1: rice 180, dal 145, total 325. After 2: rice now 2 kilo (120), total 265. After 3: dal removed, total 120. After 4: read back rice only and ask payment | 120, UPI, rice 2 kilo only |
| P05 | Hinglish | 1. "Ek paneer aur ek bread dena" 2. "Dragon fruit hai kya" 3. "Bas itna hi" 4. "Cash" | Paneer is not available today; bread added 45; "Sorry, we do not have dragon fruit"; read back bread only | 45, cash |
| P06 | Hinglish | 1. "Aadha kilo cheeni aur teen packet chai" 2. "Bas itna hi" 3. "Cash" | Half kilo sugar 22 and 3 packets of tea 360, total 382 | 382, cash |
| P07 | English | 1. "I want one five kilo bag of atta" 2. "That is all" 3. "Cash" | The 5 kg atta bag at 260 (not the loose atta) | 260, cash |
| P08 | Hindi | 1. "तीन किलो आटा चाहिए" 2. "बस इतना ही" 3. "कैश" | 3 kilo loose atta at 55 a kilo: 165 (never a bag price) | 165, cash |
| P09 | Hinglish | 1. "Ek kilo toor dal dena" 2. "Bas itna hi" 3. "Udhaar pe, mera naam Venkat hai" | Toor dal 145; finds Venkat (limit 2,000, owes 0); says his balance and the new one (145); the shopkeeper confirms | 145 on credit, customer Venkat, balance 145 |
| P10 | English | 1. "Two packets of tea" 2. "That is all" 3. "On credit, my name is Meena" 4. "Then I will pay by UPI" | Tea 240; Meena owes 1,100 of 1,200, so the credit is refused (balance would be 1,340); after 4 the order closes with UPI | 240, UPI, no credit used |
| P11 | Telugu | 1. "ఒక కిలో బియ్యం కావాలి" 2. "అంతే" 3. "అప్పు మీద, నా పేరు లక్ష్మి" | Rice 60; finds Lakshmi (limit 2,500, owes 900); new balance 960 | 60 on credit, customer Lakshmi, balance 960 |
| P12 | Hinglish | "Mera udhaar kitna hai? Mera naam Kiran hai" | Says Kiran owes 1,500 (limit 3,000); no order is created | no order file |

## B. Behaviour that is new or was fragile
| ID | What to do | The agent should |
|---|---|---|
| P13 Silent at the payment step | Order something, say "that's all", and when it asks how you will pay stay silent for a few seconds or say something unclear, then answer "cash" | "Sorry, I didn't catch that. How would you like to pay: cash, UPI or credit?" in your language, and then accept the answer |
| P14 Interrupting | Order two items; while it reads the total back, talk over it: "Nahi, ek kilo kam karo" | It stops within a moment, listens, and applies the change. It does not repeat the whole reply |
| P15 Hello and unclear start | Start with "Hello" or a mumbled word, not an order | A friendly question ("What would you like to order?"), not the same apology again and again |
| P16 Hang up mid-order | Order two items, then hang up before paying | The order is saved as **incomplete** (no payment) with those items; the dashboard shows it for the shopkeeper |
| P17 Second call at once | Right after any call, call again and place a short order | The greeting plays and the call works (calls after the first were once deaf, B-86) |
| P18 Change after payment | Complete an order with cash, then say "one more Maggi" | The addition is confirmed with the new total, not ignored |
| P19 Language switch | Start in Hindi, then ask for one item in English words | It follows you; amounts are still right |
| P20 A noisy place | Call from a market or with a fan on | Expect more mishearings; note what was lost. Not a pass or fail test |

## C. Questions about the shop (no order)
| Ask | Expected answer (from the shop's own notes) |
|---|---|
| "What are your shop hours?" | Every day, 8 AM to 9:30 PM |
| "Do you deliver? What does it cost?" | Within 3 kilometres; free for 300 rupees or more, 20 rupees for smaller orders; about 45 minutes; pick-up in about 15 minutes |
| "How can I pay?" | Cash on delivery, UPI (the shop's UPI ID is the made-up `dukaandost.demo@upi`), or credit for regular customers |
| "Do you sell dragon fruit?" | No: "Sorry, we do not have dragon fruit." It never invents an item or a price |

## D. Loan guidance (figures are computed by code and are indicative)
| ID | Say | Expected quote |
|---|---|---|
| L01 | "मुझे दुकान के लिए लोन चाहिए", then "मेरे पास एक लाख रुपये हैं" | Project cost 10 lakh, loan 9 lakh, instalment 15,438 a month |
| L02 | "నాకు రుణం కావాలి", then "నా దగ్గర యాభై వేలు ఉన్నాయి" | Project cost 5 lakh, loan 4.5 lakh, instalment 7,719 |
| L03 | "I want a loan, my whole project will cost twelve lakh rupees" | Project cost 12 lakh, loan 10.8 lakh, instalment 18,526 |
| L04 | "Business loan chahiye, main das hazaar laga sakta hoon" | Project cost 1 lakh, loan 90,000, instalment 3,034 |

The agent must say these as "indicative" and never quote a figure the code did not compute. These four are also in `evaluation/scripts/credit_loans.json`; the figures were scored there, not checked against a bank.

## Pass criteria
A conversation passes when **all** of these hold: every item and quantity that was said is in the saved order and nothing else; the spoken total equals the saved total (and the sum of the prices above); the payment is the one you chose; the agent answered in your language; no turn was left without an answer for more than about five seconds; and the call ended cleanly (an `[ORDER] call ended` line). A one-word answer that was not heard but was asked for again and then accepted still passes; write it in the notes.

## Notes sheet (copy per run)
| ID | Passed? | What was heard wrongly | What the agent said that was wrong or awkward | Seconds to first reply (rough) |
|---|---|---|---|---|

## The scripted version
`python evaluation/run_snapshot.py --runs e2e` plays `e2e_phone.json` (x01 to x12: the order and credit conversations above, with synthetic voices) through the whole agent from a frozen copy and scores them. It needs one model's daily token budget (about 12 short calls, far less than the 20-call run), and a result is quoted only if the run is valid (no refused request). The behaviours in section B need a human or a different script.
