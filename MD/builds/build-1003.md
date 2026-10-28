# Build 1003: Shopkeeper dashboard, and one agent for many shops

**Date:** 2026-10-28

## What changed
Each shop now has its own call link (/s/<shop>/) and a PIN-protected dashboard (/s/<shop>/dashboard) that shows orders, credit balances and loan enquiries live. One running agent serves any number of shops, loading each call's own prompt, stock list and greeting.

## Why
Surya asked for an admin dashboard and a shopkeeper dashboard; the shopkeeper one comes first because the demo ends on it (DEC-034). Showing a shop its own data needed a separate shop per call and a sign-in per shop.

## How it was verified
220 Python tests in a clean environment and 20 Node tests, including attempts that must fail: a wrong or another shop's PIN, repeated guessing, path-traversal shop names, and markup in an order's customer name. The real main() booted and served the dashboard and a shop call. The page was checked in headless Chrome at desktop, light-theme and 400, 390 and 360 px widths with no horizontal overflow; that check found and fixed a bug the tests missed. NOT done: the agent does not write real orders yet, so the dashboard shows only made-up demo data; the admin dashboard is not built; the dashboard was not tried on a real phone.

## What to improve next
Have the agent write orders, loan summaries and credit balances at hang-up, then the admin dashboard.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` .gitignore
- `M` CLAUDE.md
- `M` MD/DukaanDost_MASTER.md
- `M` MD/architecture.md
- `M` MD/bugs.md
- `M` MD/ci_cd.md
- `M` MD/decisions.md
- `M` MD/flow.md
- `M` MD/frontend.md
- `M` MD/poa-non-ml.md
- `M` MD/prd.md
- `M` MD/problem_statement-gap-plan.md
- `M` MD/session_handover_2026-10-28.md
- `M` MD/tasks.md
- `M` MD/tried_and_implemented.md
- `M` README.md
- `M` SETUP.md
- `M` dukaan_dost/app.py
- `A` dukaan_dost/auth.py
- `A` dukaan_dost/dashboard.py
- `A` dukaan_dost/demo_data.py
- `A` dukaan_dost/shops.py
- `A` dukaan_dost/store.py
- `M` dukaan_dost/transport.py
- `M` dukaan_dost/transport_websocket.py
- `A` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/web/index.html
- `M` local_config.example.py
- `M` scripts/check_repo.py
- `M` shops/README.md
- `M` tests/test_ci_scripts.py
- `A` tests/test_dashboard.py
- `A` tests/test_multi_shop.py
- `A` tests/test_shops_auth_store.py
- `M` tests/web/call_page.test.mjs
- `A` tests/web/dashboard.test.mjs
