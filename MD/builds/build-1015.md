# Build 1015: A sign-in page and a sign-out button instead of the browser's own box

**Date:** 2026-11-05

## What changed
Opening a shop's dashboard or the admin page while signed out now shows a proper sign-in page: a PIN field with a show button and a number pad on a phone, a keep-me-signed-in box, plain-word errors with the tries left, and a lockout countdown. The dashboard and admin top bars get a Sign out button. Sign-in is kept by a session cookie that scripts cannot read; a script can still send a Basic header.

## Why
Surya showed the browser's grey sign-in box and asked for a proper login. The box cannot say whose dashboard it is, cannot show a PIN pad, cannot count tries and looks like an error.

## How it was verified
1200 Python tests (54 new for sign-in, sessions, cookies, scopes and lockout) and 119 page tests (17 new) pass; breaking the scope check, the HttpOnly flag and the lock check each made tests fail. A real browser walked the whole flow for a shop and for the admin on fresh servers: empty, wrong and right PIN, the session working, sign out, the lockout, and the right PIN refused while locked. The browser audit has 0 errors and 0 warnings on 72 runs (9 page states, 2 themes, 4 widths); 44 of 44 contrast pairs pass. NOT done: a real phone keyboard, a real password manager, https (the Secure flag is tested, not seen), text at 1.3x.

## What to improve next
Retake the sign-in screens on a real phone; decide whether touch targets move from 44 to 48 px; show the build number in the pages.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/decisions.md
- `M` SETUP.md
- `M` dukaan_dost/admin.py
- `M` dukaan_dost/auth.py
- `M` dukaan_dost/dashboard.py
- `A` dukaan_dost/login.py
- `M` dukaan_dost/preview.py
- `M` dukaan_dost/web/admin.html
- `M` dukaan_dost/web/components/admin/topbar.html
- `M` dukaan_dost/web/components/dashboard/topbar.html
- `M` dukaan_dost/web/components/shared/icons.html
- `A` dukaan_dost/web/components/shared/login-card.html
- `A` dukaan_dost/web/components/shared/login-helpers.js
- `A` dukaan_dost/web/components/shared/login.css
- `A` dukaan_dost/web/components/shared/login.js
- `A` dukaan_dost/web/components/shared/signout-button.html
- `A` dukaan_dost/web/components/shared/signout.js
- `M` dukaan_dost/web/dashboard.html
- `A` dukaan_dost/web/login.html
- `M` dukaan_dost/webpage.py
- `A` tests/test_login.py
- `M` tests/test_webpage.py
- `A` tests/web/login.test.mjs
