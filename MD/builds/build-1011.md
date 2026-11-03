# Build 1011: The call page shows the loan quote

**Date:** 2026-11-03

## What changed
When a caller asks about a business loan, the call page now shows the quote the agent works out: the project cost, the caller's margin money, the loan, the scheme and its rate, the total interest, and the monthly instalment with how many months and the moratorium. If the loan is capped it says the caller puts in more than the margin, and if the project is above the scheme limit it says no scheme applies. It is always marked indicative.

## Why
The agent already sent the quote to the page after each answer, but the page ignored it, so a caller who asked about a loan saw nothing on screen.

## How it was verified
973 Python and 102 page tests pass. The agent's real loan session, the real transport and the real call page were run together in headless Chrome with a fake microphone, at 1280, 1100 and 390 px in light and dark with no sideways scrolling: the first quote, a replacement quote, a capped loan, a larger project, a project above the limit, the last quote staying after the call ends, and an empty panel on the next call. The page does no arithmetic and a test checks that. NOT done: a real spoken loan call through the live agent, a real phone, other browsers, Hindi or Telugu labels.

## What to improve next
Try a real spoken loan conversation end to end; check the scheme figures against an official source before they are quoted anywhere public (DEC-047).

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/frontend.md
- `M` MD/frontendgnaniskills.md
- `M` dukaan_dost/transport_websocket.py
- `M` dukaan_dost/web/components/call/helpers.js
- `M` dukaan_dost/web/components/call/layout.css
- `A` dukaan_dost/web/components/call/loan-panel.css
- `A` dukaan_dost/web/components/call/loan-panel.html
- `A` dukaan_dost/web/components/call/loan-panel.js
- `M` dukaan_dost/web/index.html
- `M` scripts/ui_check/drive.mjs
- `M` tests/web/call_page.test.mjs
