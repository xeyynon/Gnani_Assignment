# Build 1021: When a caller's payment word is not heard, the agent asks for it by name

**Date:** 2026-11-08

## What changed
At the payment step, when nothing is recognised, the agent now says 'Sorry, I didn't catch that. How would you like to pay: cash, UPI or credit?' in the caller's language instead of a bare 'please repeat'.

## Why
On the 20-call order run, the last one-word answer ('cash') was not heard on 4 of 20 calls and the caller got no hint of what to say.

## How it was verified
Three new tests (the question in English, Hindi and Telugu; the plain apology elsewhere); 1,233 Python and 130 page tests pass. Not yet heard on a real call.

## What to improve next
A real phone call that misses the word, and the 20-call run again when a model's daily budget allows

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/app.py
- `M` tests/test_lifecycle_fixes.py
