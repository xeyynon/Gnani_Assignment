# Build 1014: Every call after the first can be heard again

**Date:** 2026-11-05

## What changed
Build 1013 made the agent deaf from the second call of a session on: a reset by the recorder thread moved the call generation and the greeting for the new call was thrown away as stale. Only a hang-up and a new call move the generation now.

## Why
Build 1013 is on main with this regression; a second call in the same session heard nothing.

## How it was verified
tests/test_lifecycle_fixes.py (the exact order of events); three live calls in a row, 3 of 3 orders exactly right; 1,146 offline tests pass

## What to improve next
Valid evaluation runs on the fixed agent

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/app.py
- `M` tests/test_lifecycle_fixes.py
