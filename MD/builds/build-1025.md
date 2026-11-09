# Build 1025: The shop dashboard shows the call in progress, and the pages take the index-tab and khata look

**Date:** 2026-11-09

## What changed
A new Live view on the signed-in shop dashboard shows the conversation, the order so far and the loan quote of a call in progress, for phone calls as well as browser calls, kept in memory only. The highlights (menu tab, status tabs, notices, LIVE and OFFLINE words) now follow the picks Surya made per element.

## Why
A phone call never touched the call page, so the shopkeeper saw nothing of it (DEC-053); and the soft tinted pills, dots and bars read as generated (DEC-051).

## How it was verified
1,264 offline tests and 148 web tests pass; 62 of 62 contrast pairs pass after the merge; not tried on a real Exotel call or a real phone, and the Hindi and Telugu wording is unchecked (B-16).

## What to improve next
Try the Live view on a real phone call; tell the public call page when the line is busy; a native-speaker check of the wording.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/DukaanDost_MASTER.md
- `M` MD/decisions.md
- `M` MD/frontend.md
- `M` MD/frontendgnani.md
- `A` MD/loopfuikiller.md
- `M` dukaan_dost/dashboard.py
- `A` dukaan_dost/live_feed.py
- `M` dukaan_dost/preview.py
- `M` dukaan_dost/transport_telephony.py
- `M` dukaan_dost/transport_websocket.py
- `M` dukaan_dost/web/components/admin/layout.css
- `M` dukaan_dost/web/components/call/header.css
- `M` dukaan_dost/web/components/call/helpers.js
- `M` dukaan_dost/web/components/dashboard/helpers.js
- `A` dukaan_dost/web/components/dashboard/live-page.css
- `A` dukaan_dost/web/components/dashboard/live-page.html
- `A` dukaan_dost/web/components/dashboard/live-page.js
- `M` dukaan_dost/web/components/dashboard/side-menu.html
- `M` dukaan_dost/web/components/dashboard/topbar.html
- `M` dukaan_dost/web/components/dashboard/tour.js
- `A` dukaan_dost/web/components/shared/loan-view.js
- `M` dukaan_dost/web/components/shared/poll.js
- `M` dukaan_dost/web/components/shared/status-pill.css
- `M` dukaan_dost/web/components/shared/tokens.css
- `M` dukaan_dost/web/components/shared/topbar.css
- `M` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/web/index.html
- `A` tests/test_live_feed.py
- `M` tests/test_preview.py
- `M` tests/test_transport_telephony.py
- `M` tests/web/admin.test.mjs
- `M` tests/web/call_page.test.mjs
- `M` tests/web/dashboard.test.mjs
