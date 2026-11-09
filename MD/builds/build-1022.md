# Build 1022: A short first-visit tour, and empty lists that say what will appear

**Date:** 2026-11-09

## What changed
The shop dashboard now has a four-step tour on a first visit (the Call page link, Orders, Calls and the live-call bar) with Skip tour always there, Escape to leave it and Take the tour in the menu to see it again. Empty lists say what is missing, what will appear there and, where it helps, offer Try a call yourself.

## Why
Surya pasted a small example of an empty state and a coach-mark tour and asked for research and a version in this product (DEC-052).

## How it was verified
1227 Python tests and 133 page tests pass (6 new); contrast 62 of 62; the browser audit has no errors in 120 runs (12 page states including the tour open and an empty list, 2 themes, 5 widths down to 300 px); a real browser with a fresh profile passes 56 of 56 checks at 1280, 390 and 300 px (first visit, focus, ring around each target, tip inside the window, Done, no repeat, replay, Tab, Escape, Skip, click outside, hidden menu, blocked storage, opening at an order, the four empty lists); 168 pictures retaken. Not tried: a real phone, a real screen reader, 200% zoom, Hindi and Telugu wording.

## What to improve next
Hindi and Telugu wording for the tour (a native reader first); a tour for the admin page; decide whether the call page needs one.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/web/components/dashboard/calls-page.js
- `M` dukaan_dost/web/components/dashboard/helpers.js
- `M` dukaan_dost/web/components/dashboard/side-menu.html
- `A` dukaan_dost/web/components/dashboard/tour.css
- `A` dukaan_dost/web/components/dashboard/tour.html
- `A` dukaan_dost/web/components/dashboard/tour.js
- `M` dukaan_dost/web/components/shared/atoms.css
- `M` dukaan_dost/web/components/shared/icons.html
- `M` dukaan_dost/web/components/shared/lists.js
- `M` dukaan_dost/web/components/shared/tokens.css
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
- `A` snapshots/latest/dashboard/06-tour-step-1/dark-desktop-1280.png
- `A` snapshots/latest/dashboard/06-tour-step-1/dark-phone-390.png
- `A` snapshots/latest/dashboard/06-tour-step-1/dark-tablet-768.png
- `A` snapshots/latest/dashboard/06-tour-step-1/light-desktop-1280.png
- `A` snapshots/latest/dashboard/06-tour-step-1/light-phone-390.png
- `A` snapshots/latest/dashboard/06-tour-step-1/light-tablet-768.png
- `A` snapshots/latest/dashboard/07-tour-step-3/dark-desktop-1280.png
- `A` snapshots/latest/dashboard/07-tour-step-3/dark-phone-390.png
- `A` snapshots/latest/dashboard/07-tour-step-3/dark-tablet-768.png
- `A` snapshots/latest/dashboard/07-tour-step-3/light-desktop-1280.png
- `A` snapshots/latest/dashboard/07-tour-step-3/light-phone-390.png
- `A` snapshots/latest/dashboard/07-tour-step-3/light-tablet-768.png
- `A` snapshots/latest/dashboard/08-empty-orders/dark-desktop-1280.png
- `A` snapshots/latest/dashboard/08-empty-orders/dark-phone-390.png
- `A` snapshots/latest/dashboard/08-empty-orders/dark-tablet-768.png
- `A` snapshots/latest/dashboard/08-empty-orders/light-desktop-1280.png
- `A` snapshots/latest/dashboard/08-empty-orders/light-phone-390.png
- `A` snapshots/latest/dashboard/08-empty-orders/light-tablet-768.png
- `A` snapshots/latest/dashboard/09-empty-calls/dark-desktop-1280.png
- `A` snapshots/latest/dashboard/09-empty-calls/dark-phone-390.png
- `A` snapshots/latest/dashboard/09-empty-calls/dark-tablet-768.png
- `A` snapshots/latest/dashboard/09-empty-calls/light-desktop-1280.png
- `A` snapshots/latest/dashboard/09-empty-calls/light-phone-390.png
- `A` snapshots/latest/dashboard/09-empty-calls/light-tablet-768.png
- `M` snapshots/latest/manifest.json
- `M` snapshots/latest/reports/audit.txt
- `M` tests/web/dashboard.test.mjs
