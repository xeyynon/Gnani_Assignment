# Build 1026: The shop has a full-screen Live call page, ready for several calls

**Date:** 2026-11-09

## What changed
A new page at /s/<shop>/live shows the call in progress (the conversation, the order with its total, the loan quote, the language and the length) in large type for a big screen or a recording, behind the same shop PIN sign-in as the dashboard. With two or more calls it offers a tab for each; the agent itself still takes one call at a time.

## Why
A phone call has no call page in a browser, so the demo needs one screen that shows the call as it happens. The dashboard's Live view already holds the data; this puts it on a page of its own and keeps the rule that call text reaches only a signed-in shopkeeper.

## How it was verified
160 page tests pass in Node (12 new), test_dashboard and test_webpage pass (49, with 4 new route tests: sign-in required, this shop's PIN only, escaped shop name and locked-down policy, different from the dashboard). NOT yet seen in a real browser or with a real phone call, and the full Python suite was not rerun after the last change.

## What to improve next
Look at the page in a real browser at desktop and phone width, light and dark, then take its snapshots for the UI history. Try it during a real phone call. True parallel calls need the call server to hold more than one session.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/dashboard.py
- `A` dukaan_dost/web/components/live/calls.js
- `A` dukaan_dost/web/components/live/helpers.js
- `A` dukaan_dost/web/components/live/screen.css
- `A` dukaan_dost/web/components/live/screen.html
- `A` dukaan_dost/web/live.html
- `M` dukaan_dost/webpage.py
- `M` tests/test_dashboard.py
- `M` tests/test_webpage.py
- `A` tests/web/live.test.mjs
