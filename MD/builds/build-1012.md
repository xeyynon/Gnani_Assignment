# Build 1012: One neutral charcoal palette on every page, and bigger touch targets

**Date:** 2026-11-05

## What changed
All three pages now share one flat palette (charcoal in dark, off-white in light, one calm green) with no coloured glows, blur or gradients; the admin page no longer has its own lime look. The call page has a main landmark, and the Auto-scroll switch, the admin search box, the hide-menu button and the notice close button are large enough to tap.

## Why
Surya found the navy-and-glow dark theme too much and asked for a plainer theme everywhere. Flat solid colours also let contrast be measured exactly, and an audit of the real pages found the small targets and the missing landmark.

## How it was verified
contrast.py: all 44 measurements pass (22 pairs, light and dark). The browser audit (audit.mjs) reports 0 errors and 0 warnings on 24 runs: 3 pages, 2 themes, 360, 390, 768 and 1280 px. 102 page tests pass; the new contrast tests pass. 78 screenshots retaken and the dark call page, light admin and dark dashboard looked at. Not tried: a real phone in daylight, a live call with a microphone, 1.3x text size.

## What to improve next
Show the build number in the pages and test that it equals the tag; check a 1.3x text size and landscape phone; ask Surya whether charcoal feels too plain.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/decisions.md
- `M` dukaan_dost/web/admin.html
- `M` dukaan_dost/web/components/admin/layout.css
- `D` dukaan_dost/web/components/admin/theme.css
- `M` dukaan_dost/web/components/shared/base.css
- `D` dukaan_dost/web/components/shared/glass.css
- `M` dukaan_dost/web/components/shared/tokens.css
- `M` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/web/index.html
- `A` scripts/ui_check/contrast.py
- `A` tests/test_ui_contrast.py
- `M` tests/web/admin.test.mjs
