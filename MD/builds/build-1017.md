# Build 1017: The shop dashboard links to its own call page

**Date:** 2026-11-08

## What changed
The dashboard's side menu has a Call page link that opens the shop's own call page (/s/<shop>/), so a shopkeeper can try a call or hand the link on without typing the address.

## Why
Surya noticed there was no way from the shopkeeper's dashboard to the caller's page.

## How it was verified
1224 Python tests pass and 1 fails now and then (the replay test that InBul31 calls flaky on Windows; run alone it passed twice and failed once in three runs; this build does not touch that code); 120 page tests pass (1 new: the link for a shop path, a trailing slash, the admin and an odd path). The link was clicked in a real browser signed in to dukaan_dost and opened its call page. The dashboard pictures in snapshots/latest were retaken.

## What to improve next
Show the call link as a copyable box on the overview; show the build number in the pages.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` .gitignore
- `A` dukaan_dost/web/components/dashboard/call-link.js
- `M` dukaan_dost/web/components/dashboard/helpers.js
- `M` dukaan_dost/web/components/dashboard/side-menu.html
- `M` dukaan_dost/web/dashboard.html
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
- `M` tests/web/dashboard.test.mjs
