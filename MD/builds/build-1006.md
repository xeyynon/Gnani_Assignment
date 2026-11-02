# Build 1006: One shared colour palette for the call page and the dashboard

**Date:** 2026-11-02

## What changed
Both pages now use the Kirana Green palette: white cards on a pale slate page, green for the brand and active states, blue for sales and processing, violet for credit, amber for pending and red for errors and End call. Dark themes follow the same palette.

## Why
The two pages should look like one product, and the first redesign was too soft and mixed.

## How it was verified
396 Python and 31 Node tests pass. Both pages rendered in headless Chrome in light and dark at desktop width; status is always a coloured pill with a label. Inter is used only if installed, since the pages load nothing from outside.

## What to improve next
Try both pages on a real phone; bundle the Inter font file if the system-font fallback looks wrong.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` MD/frontend.md
- `M` dukaan_dost/web/dashboard.html
- `M` dukaan_dost/web/index.html
