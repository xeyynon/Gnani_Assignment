# Build 1018: A Calls view on the dashboard, and highlights that look like the shop's own books

**Date:** 2026-11-08

## What changed
The shop dashboard has a Calls view: every call that ended, with its language, length, what came of it and what got in the way, even when nothing was ordered. Every page now marks things its own way: a status is a tab on the card's edge, the open menu item is a tab into the page, the demo note is a paper slip, and a live call is a notched green tab on the dashboard and a pen caret elsewhere.

## Why
The hand-over of Nov 8 asked for a dashboard panel for the call records. Surya found the tinted pills, tinted menu rows, count bubbles and dots looked AI generated; two prototype looks were built (index tabs, khata ledger) and he chose element by element (DEC-051).

## How it was verified
1226 Python tests and 122 page tests pass (8 new for the Calls view and the demo calls). contrast.py passes 62 of 62 pairs (18 new). The browser audit has no errors in 80 runs (10 page states, 2 themes, 4 widths; one page re-run after Chrome did not start in time). 144 pictures retaken, none scroll sideways. Not tried: a real phone, a screen reader reading the new notice labels.

## What to improve next
Show the call link as a copyable box; decide whether call cards get the khata margin line; a real-phone look at the tabs.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/demo_data.py
- `M` dukaan_dost/web/components/admin/banner.html
- `M` dukaan_dost/web/components/admin/layout.css
- `M` dukaan_dost/web/components/call/call-card.css
- `M` dukaan_dost/web/components/call/header.css
- `M` dukaan_dost/web/components/dashboard/attention.css
- `A` dukaan_dost/web/components/dashboard/calls-page.css
- `A` dukaan_dost/web/components/dashboard/calls-page.html
- `A` dukaan_dost/web/components/dashboard/calls-page.js
- `M` dukaan_dost/web/components/dashboard/helpers.js
- `M` dukaan_dost/web/components/dashboard/layout.css
- `M` dukaan_dost/web/components/dashboard/loading.js
- `M` dukaan_dost/web/components/dashboard/side-menu.html
- `M` dukaan_dost/web/components/shared/atoms.css
- `M` dukaan_dost/web/components/shared/notices.css
- `M` dukaan_dost/web/components/shared/poll.js
- `M` dukaan_dost/web/components/shared/side-menu.css
- `M` dukaan_dost/web/components/shared/status-pill.css
- `M` dukaan_dost/web/components/shared/tokens.css
- `M` dukaan_dost/web/components/shared/topbar.css
- `M` dukaan_dost/web/dashboard.html
- `M` snapshots/latest/INDEX.md
- `M` snapshots/latest/admin/01-overview/dark-desktop-1280.png
- `M` snapshots/latest/admin/01-overview/dark-phone-390.png
- `M` snapshots/latest/admin/01-overview/dark-tablet-768.png
- `M` snapshots/latest/admin/01-overview/light-desktop-1280.png
- `M` snapshots/latest/admin/01-overview/light-phone-390.png
- `M` snapshots/latest/admin/01-overview/light-tablet-768.png
- `M` snapshots/latest/admin/02-problems/dark-desktop-1280.png
- `M` snapshots/latest/admin/02-problems/dark-phone-390.png
- `M` snapshots/latest/admin/02-problems/dark-tablet-768.png
- `M` snapshots/latest/admin/02-problems/light-desktop-1280.png
- `M` snapshots/latest/admin/02-problems/light-phone-390.png
- `M` snapshots/latest/admin/02-problems/light-tablet-768.png
- `M` snapshots/latest/admin/03-activity/dark-desktop-1280.png
- `M` snapshots/latest/admin/03-activity/dark-phone-390.png
- `M` snapshots/latest/admin/03-activity/dark-tablet-768.png
- `M` snapshots/latest/admin/03-activity/light-desktop-1280.png
- `M` snapshots/latest/admin/03-activity/light-phone-390.png
- `M` snapshots/latest/admin/03-activity/light-tablet-768.png
- `M` snapshots/latest/admin/04-add-a-shop/dark-desktop-1280.png
- `M` snapshots/latest/admin/04-add-a-shop/dark-phone-390.png
- `M` snapshots/latest/admin/04-add-a-shop/dark-tablet-768.png
- `M` snapshots/latest/admin/04-add-a-shop/light-desktop-1280.png
- `M` snapshots/latest/admin/04-add-a-shop/light-phone-390.png
- `M` snapshots/latest/admin/04-add-a-shop/light-tablet-768.png
- `M` snapshots/latest/admin/05-edit-a-working-shop/dark-desktop-1280.png
- `M` snapshots/latest/admin/05-edit-a-working-shop/dark-phone-390.png
- `M` snapshots/latest/admin/05-edit-a-working-shop/dark-tablet-768.png
- `M` snapshots/latest/admin/05-edit-a-working-shop/light-desktop-1280.png
- `M` snapshots/latest/admin/05-edit-a-working-shop/light-phone-390.png
- `M` snapshots/latest/admin/05-edit-a-working-shop/light-tablet-768.png
- `M` snapshots/latest/admin/06-edit-a-broken-shop/dark-desktop-1280.png
- `M` snapshots/latest/admin/06-edit-a-broken-shop/dark-phone-390.png
- `M` snapshots/latest/admin/06-edit-a-broken-shop/dark-tablet-768.png
- `M` snapshots/latest/admin/06-edit-a-broken-shop/light-desktop-1280.png
- `M` snapshots/latest/admin/06-edit-a-broken-shop/light-phone-390.png
- `M` snapshots/latest/admin/06-edit-a-broken-shop/light-tablet-768.png
- `M` snapshots/latest/call-page/01-idle/dark-desktop-1280.png
- `M` snapshots/latest/call-page/01-idle/dark-phone-390.png
- `M` snapshots/latest/call-page/01-idle/dark-tablet-768.png
- `M` snapshots/latest/call-page/01-idle/light-desktop-1280.png
- `M` snapshots/latest/call-page/01-idle/light-phone-390.png
- `M` snapshots/latest/call-page/01-idle/light-tablet-768.png
- `M` snapshots/latest/call-page/02-order-in-progress/dark-desktop-1280.png
- `M` snapshots/latest/call-page/02-order-in-progress/dark-phone-390.png
- `M` snapshots/latest/call-page/02-order-in-progress/dark-tablet-768.png
- `M` snapshots/latest/call-page/02-order-in-progress/light-desktop-1280.png
- `M` snapshots/latest/call-page/02-order-in-progress/light-phone-390.png
- `M` snapshots/latest/call-page/02-order-in-progress/light-tablet-768.png
- `M` snapshots/latest/call-page/03-order-and-loan-quote/dark-desktop-1280.png
- `M` snapshots/latest/call-page/03-order-and-loan-quote/dark-phone-390.png
- `M` snapshots/latest/call-page/03-order-and-loan-quote/dark-tablet-768.png
- `M` snapshots/latest/call-page/03-order-and-loan-quote/light-desktop-1280.png
- `M` snapshots/latest/call-page/03-order-and-loan-quote/light-phone-390.png
- `M` snapshots/latest/call-page/03-order-and-loan-quote/light-tablet-768.png
- `M` snapshots/latest/dashboard/01-overview/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/01-overview/dark-phone-390.png
- `M` snapshots/latest/dashboard/01-overview/dark-tablet-768.png
- `M` snapshots/latest/dashboard/01-overview/light-desktop-1280.png
- `M` snapshots/latest/dashboard/01-overview/light-phone-390.png
- `M` snapshots/latest/dashboard/01-overview/light-tablet-768.png
- `M` snapshots/latest/dashboard/02-orders/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/02-orders/dark-phone-390.png
- `M` snapshots/latest/dashboard/02-orders/dark-tablet-768.png
- `M` snapshots/latest/dashboard/02-orders/light-desktop-1280.png
- `M` snapshots/latest/dashboard/02-orders/light-phone-390.png
- `M` snapshots/latest/dashboard/02-orders/light-tablet-768.png
- `M` snapshots/latest/dashboard/03-credit-book/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/03-credit-book/dark-phone-390.png
- `M` snapshots/latest/dashboard/03-credit-book/dark-tablet-768.png
- `M` snapshots/latest/dashboard/03-credit-book/light-desktop-1280.png
- `M` snapshots/latest/dashboard/03-credit-book/light-phone-390.png
- `M` snapshots/latest/dashboard/03-credit-book/light-tablet-768.png
- `M` snapshots/latest/dashboard/04-loan-enquiries/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/04-loan-enquiries/dark-phone-390.png
- `M` snapshots/latest/dashboard/04-loan-enquiries/dark-tablet-768.png
- `M` snapshots/latest/dashboard/04-loan-enquiries/light-desktop-1280.png
- `M` snapshots/latest/dashboard/04-loan-enquiries/light-phone-390.png
- `M` snapshots/latest/dashboard/04-loan-enquiries/light-tablet-768.png
- `A` snapshots/latest/dashboard/05-calls/dark-desktop-1280.png
- `A` snapshots/latest/dashboard/05-calls/dark-phone-390.png
- `A` snapshots/latest/dashboard/05-calls/dark-tablet-768.png
- `A` snapshots/latest/dashboard/05-calls/light-desktop-1280.png
- `A` snapshots/latest/dashboard/05-calls/light-phone-390.png
- `A` snapshots/latest/dashboard/05-calls/light-tablet-768.png
- `A` snapshots/latest/manifest.json
- `M` snapshots/latest/reports/audit.txt
- `M` snapshots/latest/reports/contrast.md
- `M` snapshots/latest/sign-in-admin/02-wrong-password/dark-phone-390.png
- `M` tests/test_shops_auth_store.py
- `M` tests/web/admin.test.mjs
- `M` tests/web/dashboard.test.mjs
