# Build 1023: A caller's "that's all" is no longer missed, and a thank-you after payment is answered with thanks

**Date:** 2026-11-08

## What changed
A sentence that adds an item and ends with a clear 'that's all' (in English, Hindi, Hinglish or Telugu) now closes the list even when the model misses it; once an order is complete a thank-you or a repeated 'that's all' gets 'Thank you! Your order is noted' instead of the whole order read back again; and a bare English payment word such as 'cash' no longer switches a Hindi or Telugu call to English.

## Why
The second and third real phone calls (2026-11-09) showed the order read back twice after the payment and 'Anything else?' asked after a thank-you, a one-sentence order whose 'that's all' was ignored, and the whole reply language flipping to English on one word.

## How it was verified
New tests for the phrases, the thanks and the language rule; the 8 scripted credit and loan calls on gpt-oss-120b after the first two changes were 4 of 4 orders and 4 of 4 loans exactly right with no refused request; 1,265 Python tests pass. The last two refinements (filler words after the phrase, the language rule) were not part of that run and have not been heard on a real call.

## What to improve next
Conversations 1 to 20 of the test sheet on the phone, and the 12 scripted end-to-end calls when a model's budget allows

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/app.py
- `M` dukaan_dost/conversation_manager.py
- `M` dukaan_dost/order_session.py
- `M` dukaan_dost/order_turn.py
- `M` tests/test_lifecycle_fixes.py
- `M` tests/test_order_turn.py
