# Build 1019: A Telugu call that Prisma first hears as Hindi is no longer decoded as Hindi

**Date:** 2026-11-08

## What changed
The speech recogniser is now told the call's language only when it is Telugu. Naming Hindi kept a Telugu call decoded as Hindi after one wrong first guess, and a loan call was lost.

## Why
The first rerun of the credit and loan calls after Build 1016 got 3 of 4 loan calls: the Telugu loan call was heard as Hindi on its first turn, the call was locked to Hindi and the next turn was decoded as Hindi nonsense.

## How it was verified
The same 8 scripted credit and loan calls on gpt-oss-120b after the change: 4 of 4 orders and 4 of 4 loans exactly right, every turn answered, no refused request (credit_loans_clean_120b); the full suite passes

## What to improve next
The valid 20-call order run tonight, and a real phone call in Telugu

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/app.py
- `M` tests/test_lifecycle_fixes.py
