# Build 1020: From a call to its order, a clearer live label, and fixes from a full UI test pass

**Date:** 2026-11-09

## What changed
On the dashboard an ordered call now has a View order link that opens that order, and an order you open stays open instead of snapping shut every 3 seconds. Whether the data is fresh is said in a word, a green LIVE or a red OFFLINE tab, with no dot, bar or blinking. Long unbroken text no longer pushes the page sideways, the admin search no longer scrolls a zoomed phone sideways, icons are hidden from screen readers, and notices are announced.

## Why
Surya asked for the Calls view to be finished, for proper testing of every aspect of the UI, and not to have vertical-bar designs; three testers worked in parallel and their findings were fixed (frontend.md, section A full UI test pass).

## How it was verified
1226 Python tests pass and 1 test of the agent's call handling failed in both full runs (it passes 5 of 5 on its own; it waits on timing and is not touched by this build); 130 page tests pass (13 new this round); contrast 62 of 62; the browser audit has no errors in 100 runs (10 page states, 2 themes, 5 widths, including 300 px, the same as 130% zoom; 10 re-run after Chrome failed to start once); a real-browser test of the View order link passes 12 of 12; 51 of 51 extreme-data cases pass at 1280, 390 and 300 px; 144 pictures retaken. Not fixed and listed in frontend.md: 200% zoom on a phone, some small touch targets on the admin edit page, the PIN show button moving focus. Not tried: a real phone, a real screen reader, Start call.

## What to improve next
The open items in frontend.md; ask the backend session to look at the flaky call-handling test.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/demo_data.py
- `M` dukaan_dost/web/components/admin/activity.html
- `M` dukaan_dost/web/components/admin/add-shop.html
- `M` dukaan_dost/web/components/admin/banner.html
- `M` dukaan_dost/web/components/admin/edit-shop.html
- `M` dukaan_dost/web/components/admin/layout.css
- `M` dukaan_dost/web/components/admin/overview-panels.html
- `M` dukaan_dost/web/components/admin/problems.html
- `M` dukaan_dost/web/components/admin/shops.html
- `M` dukaan_dost/web/components/admin/side-menu.html
- `M` dukaan_dost/web/components/admin/topbar.html
- `M` dukaan_dost/web/components/call/call-card.html
- `M` dukaan_dost/web/components/call/header.html
- `M` dukaan_dost/web/components/call/loan-panel.html
- `M` dukaan_dost/web/components/call/order-panel.html
- `M` dukaan_dost/web/components/call/tips.html
- `M` dukaan_dost/web/components/call/transcript.css
- `M` dukaan_dost/web/components/call/transcript.html
- `M` dukaan_dost/web/components/dashboard/attention.html
- `M` dukaan_dost/web/components/dashboard/calls-page.css
- `M` dukaan_dost/web/components/dashboard/calls-page.js
- `M` dukaan_dost/web/components/dashboard/helpers.js
- `M` dukaan_dost/web/components/dashboard/layout.css
- `M` dukaan_dost/web/components/dashboard/loans-page.js
- `A` dukaan_dost/web/components/dashboard/order-jump.js
- `M` dukaan_dost/web/components/dashboard/orders-page.js
- `M` dukaan_dost/web/components/dashboard/quick-actions.html
- `M` dukaan_dost/web/components/dashboard/recent-orders.html
- `M` dukaan_dost/web/components/dashboard/sales-trend.html
- `M` dukaan_dost/web/components/dashboard/side-menu.html
- `M` dukaan_dost/web/components/dashboard/topbar.html
- `M` dukaan_dost/web/components/shared/atoms.css
- `M` dukaan_dost/web/components/shared/brand.html
- `M` dukaan_dost/web/components/shared/dom.js
- `M` dukaan_dost/web/components/shared/lists.css
- `M` dukaan_dost/web/components/shared/login-card.html
- `M` dukaan_dost/web/components/shared/menu-head.html
- `M` dukaan_dost/web/components/shared/menu-show.html
- `M` dukaan_dost/web/components/shared/notices.css
- `M` dukaan_dost/web/components/shared/poll.js
- `M` dukaan_dost/web/components/shared/shell.css
- `M` dukaan_dost/web/components/shared/signout-button.html
- `M` dukaan_dost/web/components/shared/theme-button.html
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
- `M` snapshots/latest/dashboard/05-calls/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/05-calls/dark-phone-390.png
- `M` snapshots/latest/dashboard/05-calls/dark-tablet-768.png
- `M` snapshots/latest/dashboard/05-calls/light-desktop-1280.png
- `M` snapshots/latest/dashboard/05-calls/light-phone-390.png
- `M` snapshots/latest/dashboard/05-calls/light-tablet-768.png
- `M` snapshots/latest/reports/audit.txt
- `M` tests/test_shops_auth_store.py
- `M` tests/web/admin.test.mjs
- `M` tests/web/call_page.test.mjs
- `M` tests/web/dashboard.test.mjs
