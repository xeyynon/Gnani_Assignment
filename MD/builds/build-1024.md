# Build 1024: The pages hold together when zoomed in to 200% on a phone

**Date:** 2026-11-09

## What changed
At 130%, 150% and 200% browser zoom on a phone the dashboard, call page and admin page no longer scroll sideways and stay readable: Recent orders stack into one column, tile figures stay whole, the sales chart labels every other day, panel tags and the Auto-scroll switch drop under their title, quick actions and the admin notice wrap, and the admin stock checkboxes are big enough to press.

## Why
Zoom was an open gap after the full UI test pass, and Surya asked to work on it.

## How it was verified
136 page tests pass (3 new for these rules); 209 page-related Python tests pass; contrast 62 of 62; the browser audit has no errors in 144 runs (12 page states, 2 themes, 6 widths from 195 px, which is a 390 px phone at 200% zoom, to 1280 px); 168 pictures retaken and the dashboard at 195 and 260 px looked at, which found a crushed orders table and cut-up figures that the audit cannot see. Not tried: a real phone at 200% zoom, a bigger system font size (not the same as browser zoom), the three 17 px links on the admin edit page.

## What to improve next
Try it on a real phone; the 17 px links on the admin edit page; Hindi and Telugu wording for the tour.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/web/components/admin/layout.css
- `M` dukaan_dost/web/components/dashboard/attention.css
- `M` dukaan_dost/web/components/dashboard/recent-orders.css
- `M` dukaan_dost/web/components/dashboard/recent-orders.js
- `M` dukaan_dost/web/components/dashboard/sales-trend.css
- `M` dukaan_dost/web/components/shared/panel.css
- `M` dukaan_dost/web/components/shared/quick-actions.css
- `M` dukaan_dost/web/components/shared/tile.css
- `M` snapshots/latest/INDEX.md
- `M` snapshots/latest/admin/01-overview/dark-desktop-1280.png
- `M` snapshots/latest/admin/01-overview/dark-phone-390.png
- `M` snapshots/latest/admin/01-overview/dark-tablet-768.png
- `M` snapshots/latest/admin/01-overview/light-desktop-1280.png
- `M` snapshots/latest/admin/01-overview/light-phone-390.png
- `M` snapshots/latest/admin/01-overview/light-tablet-768.png
- `M` snapshots/latest/admin/02-problems/dark-phone-390.png
- `M` snapshots/latest/admin/02-problems/dark-tablet-768.png
- `M` snapshots/latest/admin/02-problems/light-desktop-1280.png
- `M` snapshots/latest/admin/02-problems/light-phone-390.png
- `M` snapshots/latest/admin/02-problems/light-tablet-768.png
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
- `M` snapshots/latest/dashboard/06-tour-step-1/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/06-tour-step-1/dark-phone-390.png
- `M` snapshots/latest/dashboard/06-tour-step-1/dark-tablet-768.png
- `M` snapshots/latest/dashboard/06-tour-step-1/light-desktop-1280.png
- `M` snapshots/latest/dashboard/06-tour-step-1/light-phone-390.png
- `M` snapshots/latest/dashboard/06-tour-step-1/light-tablet-768.png
- `M` snapshots/latest/dashboard/07-tour-step-3/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/07-tour-step-3/dark-phone-390.png
- `M` snapshots/latest/dashboard/07-tour-step-3/dark-tablet-768.png
- `M` snapshots/latest/dashboard/07-tour-step-3/light-desktop-1280.png
- `M` snapshots/latest/dashboard/07-tour-step-3/light-phone-390.png
- `M` snapshots/latest/dashboard/07-tour-step-3/light-tablet-768.png
- `M` snapshots/latest/dashboard/08-empty-orders/dark-phone-390.png
- `M` snapshots/latest/dashboard/08-empty-orders/dark-tablet-768.png
- `M` snapshots/latest/dashboard/08-empty-orders/light-desktop-1280.png
- `M` snapshots/latest/dashboard/08-empty-orders/light-tablet-768.png
- `M` snapshots/latest/dashboard/09-empty-calls/dark-desktop-1280.png
- `M` snapshots/latest/dashboard/09-empty-calls/dark-phone-390.png
- `M` snapshots/latest/dashboard/09-empty-calls/dark-tablet-768.png
- `M` snapshots/latest/dashboard/09-empty-calls/light-desktop-1280.png
- `M` snapshots/latest/dashboard/09-empty-calls/light-tablet-768.png
- `M` snapshots/latest/reports/audit.txt
- `M` snapshots/latest/sign-in-shop/06-locked/dark-phone-390.png
- `M` tests/web/admin.test.mjs
- `M` tests/web/call_page.test.mjs
- `M` tests/web/dashboard.test.mjs
