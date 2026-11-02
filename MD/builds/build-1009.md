# Build 1009: The admin dashboard: look after every shop from one page

**Date:** 2026-11-02

## What changed
The admin page at /admin shows every shop with a state, the calls in progress, orders today and a list of what is wrong with each shop. From it the operator can add a shop (blank or a copy of one) with its PIN, set a new PIN, edit a shop's instructions and stock list, and mark warnings solved. Every change is recorded in an activity log. The agent picks a shop's changes up on its next call.

## Why
Shops were added by copying folders and running a command, and a broken shop could not take a call without anyone knowing why.

## How it was verified
745 Python and 78 page tests pass. The real page was driven in headless Chrome through 20 flows (add a shop, a duplicate refused, a generated PIN, edit instructions, an empty prompt refused, add and change and remove stock, set a PIN, mark solved and undo, a hostile shop name shown as text) and checked for sideways scrolling. Sign-in, a shop's PIN not opening the page, a page on another site not being able to use the command socket, and that no PIN or prompt reaches the activity log are each tested. NOT done: a real phone, running it against the real agent with real shops, failed turns per shop, or deleting a shop (deliberately not offered).

## What to improve next
Dark look and search, filter tabs and an activity view for the admin page; try it against the real agent; record failed turns so the problem list can show them.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/decisions.md
- `M` MD/frontend.md
- `M` MD/tasks.md
- `A` dukaan_dost/admin.py
- `A` dukaan_dost/admin_actions.py
- `M` dukaan_dost/app.py
- `M` dukaan_dost/auth.py
- `M` dukaan_dost/preview.py
- `A` dukaan_dost/shop_health.py
- `M` dukaan_dost/shops.py
- `M` dukaan_dost/transport_websocket.py
- `A` dukaan_dost/web/admin.html
- `A` dukaan_dost/web/components/admin/add-shop.html
- `A` dukaan_dost/web/components/admin/add-shop.js
- `A` dukaan_dost/web/components/admin/commands.js
- `A` dukaan_dost/web/components/admin/edit-shop.html
- `A` dukaan_dost/web/components/admin/edit-shop.js
- `A` dukaan_dost/web/components/admin/helpers.js
- `A` dukaan_dost/web/components/admin/layout.css
- `A` dukaan_dost/web/components/admin/loading.js
- `A` dukaan_dost/web/components/admin/problems.html
- `A` dukaan_dost/web/components/admin/problems.js
- `A` dukaan_dost/web/components/admin/shops.html
- `A` dukaan_dost/web/components/admin/shops.js
- `A` dukaan_dost/web/components/admin/side-menu.html
- `A` dukaan_dost/web/components/admin/stat-tiles.html
- `A` dukaan_dost/web/components/admin/stat-tiles.js
- `A` dukaan_dost/web/components/admin/topbar.html
- `M` dukaan_dost/web/components/dashboard/helpers.js
- `M` dukaan_dost/web/components/dashboard/layout.css
- `R` dukaan_dost/web/components/dashboard/skeleton.js → dukaan_dost/web/components/dashboard/loading.js
- `M` dukaan_dost/web/components/dashboard/side-menu.html
- `M` dukaan_dost/web/components/dashboard/stat-tiles.js
- `M` dukaan_dost/web/components/dashboard/topbar.html
- `A` dukaan_dost/web/components/shared/bento.css
- `M` dukaan_dost/web/components/shared/format.js
- `A` dukaan_dost/web/components/shared/forms.css
- `R` dukaan_dost/web/components/dashboard/greeting.css → dukaan_dost/web/components/shared/greeting.css
- `R` dukaan_dost/web/components/dashboard/icon-tile.css → dukaan_dost/web/components/shared/icon-tile.css
- `M` dukaan_dost/web/components/shared/icons.html
- `R` dukaan_dost/web/components/dashboard/lists.css → dukaan_dost/web/components/shared/lists.css
- `R` dukaan_dost/web/components/dashboard/lists.js → dukaan_dost/web/components/shared/lists.js
- `A` dukaan_dost/web/components/shared/menu-head.html
- `A` dukaan_dost/web/components/shared/menu-helpers.js
- `R` dukaan_dost/web/components/dashboard/menu-init.html → dukaan_dost/web/components/shared/menu-init.html
- `A` dukaan_dost/web/components/shared/menu-show.html
- `R` dukaan_dost/web/components/dashboard/menu.js → dukaan_dost/web/components/shared/menu.js
- `R` dukaan_dost/web/components/dashboard/notices.css → dukaan_dost/web/components/shared/notices.css
- `A` dukaan_dost/web/components/shared/poll.js
- `R` dukaan_dost/web/components/dashboard/quick-actions.css → dukaan_dost/web/components/shared/quick-actions.css
- `A` dukaan_dost/web/components/shared/shell.css
- `R` dukaan_dost/web/components/dashboard/side-menu.css → dukaan_dost/web/components/shared/side-menu.css
- `R` dukaan_dost/web/components/dashboard/skeleton.css → dukaan_dost/web/components/shared/skeleton.css
- `A` dukaan_dost/web/components/shared/skeleton.js
- `R` dukaan_dost/web/components/dashboard/status-pill.css → dukaan_dost/web/components/shared/status-pill.css
- `R` dukaan_dost/web/components/dashboard/stat-tiles.css → dukaan_dost/web/components/shared/tile.css
- `A` dukaan_dost/web/components/shared/tile.js
- `R` dukaan_dost/web/components/dashboard/topbar.css → dukaan_dost/web/components/shared/topbar.css
- `R` dukaan_dost/web/components/dashboard/views.js → dukaan_dost/web/components/shared/views.js
- `M` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/webpage.py
- `A` tests/test_admin.py
- `A` tests/test_admin_actions.py
- `A` tests/test_admin_activity.py
- `A` tests/test_admin_socket.py
- `A` tests/test_shop_health.py
- `M` tests/test_shops_auth_store.py
- `M` tests/test_webpage.py
- `A` tests/web/admin.test.mjs
