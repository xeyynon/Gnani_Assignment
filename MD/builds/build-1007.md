# Build 1007: Pages built from components, with a bento and glass design, a hideable menu and a fair yesterday comparison

**Date:** 2026-11-02

## What changed
The call page and the dashboard are now built from small components that the server stitches together when a page is served. They have a new look that mixes a bento grid, glass for the menu and bars, and hard-edged accents on the call button and the hero Sales figure. The dashboard menu is a curved drawer that slides out and can be hidden, with a theme switch (Auto, Light, Dark) on both pages. The dashboard compares today with yesterday up to the same time of day, shows loading placeholders instead of blank panels, and folds the needs-attention count into its panel.

## Why
The two pages were 500-line files with the same pieces written twice, and Surya builds interfaces component by component. The old look was a plain list, and early in the day today was being measured against all of yesterday.

## How it was verified
558 Python and 49 page tests pass. Sideways scrolling checked at 1440, 1280, 1100, 1001, 900, 600, 390 and 360 px with the menu open, and at 1440, 1100 and 390 px with it hidden. CSS compared rule by rule before and after the split. A stray colour put into each kind of component fails the colour test. Screenshots at desktop and phone widths in light and dark. NOT done: a real phone, a real microphone, or a contrast tool.

## What to improve next
Try both pages on a real phone and with a real call; measure contrast with a tool; decide whether the brutalist accents are strong enough.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/frontend.md
- `M` dukaan_dost/dashboard.py
- `M` dukaan_dost/store.py
- `M` dukaan_dost/transport_websocket.py
- `A` dukaan_dost/web/components/call/audio-capture.js
- `A` dukaan_dost/web/components/call/call-card.css
- `A` dukaan_dost/web/components/call/call-card.html
- `A` dukaan_dost/web/components/call/header.css
- `A` dukaan_dost/web/components/call/header.html
- `A` dukaan_dost/web/components/call/helpers.js
- `A` dukaan_dost/web/components/call/layout.css
- `A` dukaan_dost/web/components/call/order-panel.css
- `A` dukaan_dost/web/components/call/order-panel.html
- `A` dukaan_dost/web/components/call/order-panel.js
- `A` dukaan_dost/web/components/call/tips.css
- `A` dukaan_dost/web/components/call/tips.html
- `A` dukaan_dost/web/components/call/transcript.css
- `A` dukaan_dost/web/components/call/transcript.html
- `A` dukaan_dost/web/components/call/transcript.js
- `A` dukaan_dost/web/components/call/waveform.js
- `A` dukaan_dost/web/components/dashboard/attention.css
- `A` dukaan_dost/web/components/dashboard/attention.html
- `A` dukaan_dost/web/components/dashboard/attention.js
- `A` dukaan_dost/web/components/dashboard/credit-page.html
- `A` dukaan_dost/web/components/dashboard/credit-page.js
- `A` dukaan_dost/web/components/dashboard/greeting.css
- `A` dukaan_dost/web/components/dashboard/greeting.html
- `A` dukaan_dost/web/components/dashboard/helpers.js
- `A` dukaan_dost/web/components/dashboard/icon-tile.css
- `A` dukaan_dost/web/components/dashboard/layout.css
- `A` dukaan_dost/web/components/dashboard/lists.css
- `A` dukaan_dost/web/components/dashboard/lists.js
- `A` dukaan_dost/web/components/dashboard/loans-page.html
- `A` dukaan_dost/web/components/dashboard/loans-page.js
- `A` dukaan_dost/web/components/dashboard/menu-init.html
- `A` dukaan_dost/web/components/dashboard/menu.js
- `A` dukaan_dost/web/components/dashboard/notices.css
- `A` dukaan_dost/web/components/dashboard/orders-page.html
- `A` dukaan_dost/web/components/dashboard/orders-page.js
- `A` dukaan_dost/web/components/dashboard/quick-actions.css
- `A` dukaan_dost/web/components/dashboard/quick-actions.html
- `A` dukaan_dost/web/components/dashboard/recent-orders.css
- `A` dukaan_dost/web/components/dashboard/recent-orders.html
- `A` dukaan_dost/web/components/dashboard/recent-orders.js
- `A` dukaan_dost/web/components/dashboard/sales-trend.css
- `A` dukaan_dost/web/components/dashboard/sales-trend.html
- `A` dukaan_dost/web/components/dashboard/sales-trend.js
- `A` dukaan_dost/web/components/dashboard/side-menu.css
- `A` dukaan_dost/web/components/dashboard/side-menu.html
- `A` dukaan_dost/web/components/dashboard/skeleton.css
- `A` dukaan_dost/web/components/dashboard/skeleton.js
- `A` dukaan_dost/web/components/dashboard/stat-tiles.css
- `A` dukaan_dost/web/components/dashboard/stat-tiles.html
- `A` dukaan_dost/web/components/dashboard/stat-tiles.js
- `A` dukaan_dost/web/components/dashboard/status-pill.css
- `A` dukaan_dost/web/components/dashboard/topbar.css
- `A` dukaan_dost/web/components/dashboard/topbar.html
- `A` dukaan_dost/web/components/dashboard/views.js
- `A` dukaan_dost/web/components/shared/atoms.css
- `A` dukaan_dost/web/components/shared/base.css
- `A` dukaan_dost/web/components/shared/brand.html
- `A` dukaan_dost/web/components/shared/brutal.css
- `A` dukaan_dost/web/components/shared/dom.js
- `A` dukaan_dost/web/components/shared/format.js
- `A` dukaan_dost/web/components/shared/glass.css
- `A` dukaan_dost/web/components/shared/icons.html
- `A` dukaan_dost/web/components/shared/keys.js
- `A` dukaan_dost/web/components/shared/panel.css
- `A` dukaan_dost/web/components/shared/theme-button.css
- `A` dukaan_dost/web/components/shared/theme-button.html
- `A` dukaan_dost/web/components/shared/theme-helpers.js
- `A` dukaan_dost/web/components/shared/theme-init.html
- `A` dukaan_dost/web/components/shared/theme.js
- `A` dukaan_dost/web/components/shared/tokens.css
- `M` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/web/index.html
- `A` dukaan_dost/webpage.py
- `M` tests/test_shops_auth_store.py
- `A` tests/test_webpage.py
- `M` tests/web/call_page.test.mjs
- `A` tests/web/composed.mjs
- `M` tests/web/dashboard.test.mjs
