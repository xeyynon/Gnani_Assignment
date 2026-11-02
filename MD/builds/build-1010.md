# Build 1010: The admin page gets a dark look, search, filter tabs, a notice, an activity view and overview panels

**Date:** 2026-11-02

## What changed
The admin page now starts dark, with near-black surfaces and a lime accent for what is active; the shop pages are unchanged. It has a Workspace label in the menu, a search box (Ctrl or Cmd K), filter tabs with counts, a notice that stays dismissed until the numbers change, an Activity view of what was changed, overview panels with View all links, and a Copy call link button on each shop.

## Why
Surya asked for the admin to take its look and some of its functions from a reference dark dashboard, and an admin needs to find a shop quickly, see what changed, and send a shop's call link.

## How it was verified
748 Python and 93 page tests pass. The real page was driven through its flows in headless Chrome at 1280 px light and 390 px dark with no sideways scrolling: tabs and their counts, search and Escape, Ctrl+K, the notice and its dismissal, the activity view with no PIN in it, the overview panels, and the copy button with its fallback. NOT done: a real phone, contrast measured with a tool, browsers other than Chrome, and the reference site's exact colours (a text fetch returns structure, not styling).

## What to improve next
Try it against the real agent with real shops; consider Show more on the shops list once there are dozens; measure contrast.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/web/admin.html
- `A` dukaan_dost/web/components/admin/activity.html
- `A` dukaan_dost/web/components/admin/activity.js
- `A` dukaan_dost/web/components/admin/banner.html
- `A` dukaan_dost/web/components/admin/banner.js
- `M` dukaan_dost/web/components/admin/helpers.js
- `M` dukaan_dost/web/components/admin/layout.css
- `M` dukaan_dost/web/components/admin/loading.js
- `A` dukaan_dost/web/components/admin/overview-panels.html
- `A` dukaan_dost/web/components/admin/overview-panels.js
- `M` dukaan_dost/web/components/admin/shops.html
- `M` dukaan_dost/web/components/admin/shops.js
- `M` dukaan_dost/web/components/admin/side-menu.html
- `A` dukaan_dost/web/components/admin/theme-default.html
- `A` dukaan_dost/web/components/admin/theme.css
- `M` dukaan_dost/web/components/admin/topbar.html
- `M` dukaan_dost/web/components/shared/icons.html
- `M` dukaan_dost/web/components/shared/theme-init.html
- `M` dukaan_dost/web/components/shared/theme.js
- `M` tests/web/admin.test.mjs
