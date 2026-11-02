# Frontend

Three pages, all served by the agent on one port. Two exist; the admin one is planned.

| Page | Address | Who | Status |
|---|---|---|---|
| Call page | `/s/<shop>/` (and `/` for the default shop) | The caller | Built (Build 1002) |
| Shopkeeper dashboard | `/s/<shop>/dashboard` | The shop's owner, with the shop's PIN | Built (Build 1003) |
| Admin dashboard | `/admin` | You, with the admin password | Planned (DEC-034) |

## Design system (both pages)
One palette, chosen 2026-11-02: solid cards on a soft page, **Kirana Green** `#16803D` as the brand colour, blue for sales and "processing", violet for credit (udhaar), amber for pending, red for errors and the end-call button (`#DC2626`). Status is always a coloured pill **with a label**, never colour alone. Cards have a 14 px radius, buttons 9 px, a 1 px `#E2E8F0` border and a very light shadow; no gradients. Dark themes follow the device. Text is Inter when installed, otherwise the system font (the pages load nothing from outside, so Inter cannot be fetched). The tokens live in `components/shared/tokens.css`, one copy for both pages.

## UI rules, learned from an earlier project's frontend guide (2026-11-02)
Taken as principles, not content, and each one checked against these two pages first. What was already right: colours as tokens, status as a labelled pill, three kinds of empty (waiting, none, not available), server text shown as text only, reduced motion handled.

Changed because of it:
- **A theme control on every page.** Auto, Light, Dark; the choice is remembered (`dd:theme`) and applied by a small script in `<head>` before the CSS, so there is no flash. Before this the pages followed only the device, so a change to the light theme was invisible on a dark device. Press `T`.
- **Loading is not "nothing here".** The dashboard shows placeholder blocks until the first answer, and marks `main` busy; the empty-state messages are only for data that really is empty. A week with no sales shows one empty message, not seven zero bars.
- **Compare like with like.** "vs yesterday" now compares today so far with yesterday up to the same time of day (`*_yesterday_same_time` in the snapshot), and says "vs this time yesterday". Older servers fall back to the whole of yesterday.
- **Focus never falls to the page.** When Start call becomes End call, focus moves to the new button; when a dashboard section changes, focus moves to its heading.
- **Keys:** `M` mutes during a call, `T` changes the theme; both ignore typing, held keys and Ctrl/Alt/Cmd chords, and the key is shown in the control's tooltip.
- **Touch targets** are 44 px on a coarse pointer.
- **Every colour is a token**, including the text on the green and red buttons. A test fails if a colour is written anywhere else in either page.

Rules to keep:
1. A rule that has been decided gets a check in the same change (the colour test is the model). A check must be seen to **fail** once: the first version of that test could never fail, because an escape turned `` into a backspace byte, and it passed on every run until a stray colour was injected on purpose.
2. Show only what the data supports: a missing value is a dash or a stated reason, never a placeholder that looks like a reading.
3. State that the user chose lives in one place and survives navigation; everything else stays local.
4. Every piece of the interface is a component with one home (see Component structure).

Not taken: a router, a state library, lazy-loaded screens, a status page and a build-label dialog. They solve problems these two small pages do not have yet.

## The visual mix: bento, glass, brutalist accents, minimal (DEC-041)
Four design ideas, each with one job so they do not fight:

| Idea | Its job | Where it lives |
|---|---|---|
| **Bento** | The layout: unequal cells on a 12-column grid, one hero | `dashboard/layout.css` (the overview), `call/layout.css`; panels carry `b-*` classes |
| **Glass** | The chrome only: side menu, top bar, chips, small buttons, the call card, floating over soft colour blobs | `shared/glass.css`; tokens `--glass`, `--glass-line`, `--blur`, `--blob-1..3` |
| **Brutalist accents** | The few things that matter most: a thick border and a hard offset shadow that presses in on click (the call button, End call, the hero number); monospace numerals; small uppercase labels | `shared/brutal.css` (class `brut`); `--mono`, `--brut`, `--hard-shadow` |
| **Minimal** | The base: one 22 px radius, generous gaps, no shadows on ordinary cells, nothing decorative beyond the above | `shared/tokens.css` |

- **The side menu is a drawer** (2026-11-02): a floating panel with a large curved right end, coming out from the left edge. A chevron button inside it hides it (it slides out and the page widens); a panel icon in the top bar brings it back; `B` does both. The choice is remembered (`dd:menu`) and applied by a small script in `<head>` before the CSS, so there is no flash. While hidden the menu leaves the tab order, and focus moves to the button that replaces the one pressed. On a phone the menu row is hidden entirely and the same icon brings it back. Components: `dashboard/side-menu.*`, `dashboard/menu.js`, `dashboard/menu-init.html`.
- **The hero tile is one row, not two:** the Sales tile is the widest and has the biggest number but is no taller than its neighbours; a first version two rows tall was mostly empty. The three tiles are one row on a laptop, and the check for sideways scrolling is run at 1440, 1280, 1100, 1001, 900, 600, 390 and 360 px, menu open and hidden.

Rules that keep the mix honest:
1. **Glass never carries a number.** Cards with figures (the tiles, the order table, the lists, the chart) are solid. Glass has an opaque fallback where `backdrop-filter` is missing and under `prefers-reduced-transparency`.
2. **Brutalism is an accent, never the base.** Use `brut` on at most the one call to action and the one hero figure per screen. It respects reduced motion (the press animation only runs when motion is allowed).
3. **One hero per page.** On the dashboard it is Sales today (tall, blue, hard-edged); on the call page it is the call card.
4. **Colours still come only from tokens.** The blob colours, the glass tints and the brutalist ink are tokens in each theme (the brutalist ink is dark green-black in light and the brand green in dark). The colour test covers the new files.
5. **Cells dissolve into the grid.** On the dashboard the old wrappers (`.cols`, `.stack`, the tile row) are `display:contents` so each cell is placed directly by its `b-*` class. Phone: two columns, then one, hero first.

## Component structure (DEC-040)
Everything on the two pages is a **component**: one small file with one job, composed into a page. A page file (`dukaan_dost/web/index.html`, `dashboard.html`) is only a list of the components it is made of plus its own controller; the pieces live in `dukaan_dost/web/components/`. The server stitches them together on every request (`dukaan_dost/webpage.py`, `{{include:path}}`), so each page still arrives as **one self-contained response** and the dashboard's strict content security policy (no outside files) is unchanged.

Levels, from the smallest piece up:

| Level | What it is | Where | Examples |
|---|---|---|---|
| **Tokens** | The colours, radii and shadow. The only place a colour is written. | `shared/tokens.css` | light, device-dark, chosen-dark |
| **Atoms** | One visual idea, no layout of its own | `shared/atoms.css`, `shared/base.css`, `shared/icons.html` | `.mark`, `.chip`, `.dot`, `.tag`, `.soon`, `.empty`, the icon sheet |
| **Molecules** | A few atoms that work together | `shared/panel.css`, `shared/brand.html`, `shared/theme-button.*`, `dashboard/status-pill.css`, `dashboard/icon-tile.css` | panel with its heading row, the brand block, the theme button, the status pill |
| **Organisms** | A whole panel: its markup, its styles and its script, side by side | `dashboard/recent-orders.*`, `dashboard/stat-tiles.*`, `dashboard/attention.*`, `dashboard/sales-trend.*`, `call/call-card.*`, `call/transcript.*`, `call/order-panel.*` | "Recent orders", the four number tiles, the live transcript |
| **Pages** | The list of organisms and the controller that feeds them | `index.html`, `dashboard.html` | the call page, the dashboard |

An organism is up to three files with the same name: `x.html` (markup), `x.css` (styles), `x.js` (the function that draws it). **Pure helpers** (formatting, labels, the "needs attention" rule) sit in `helpers.js` files between the `helpers` markers in the page script, so Node tests can run them without a browser.

Rules:
1. **One home per piece.** If two pages need the same thing it goes in `shared/`; a piece used by one page lives under that page's folder. The theme button, the brand block, the colour tokens, the icon sheet, the DOM builder `h()`, the formatters and the shortcut check used to be written twice; each now exists once.
2. **A component is one kind of thing** (markup, styles *or* script) and never holds its own `<script>` or `<style>` tag; the page owns those. A test fails otherwise.
3. **No orphans, no holes.** A test fails if a component file is used by no page, or if a page asks for one that does not exist. A missing component is a build error, never a silent gap.
4. **Names do not collide in meaning.** A class means one thing everywhere: the call page's order total is `.order-total` (the dashboard's `.total` is a different thing), its shop pill is `.shop-chip` (the dashboard's `.shop` is a different thing).
5. **Change a token, change it in `shared/tokens.css` only.** Pages no longer have their own copies to keep identical (this used to be a manual rule and is now structural).
6. **Look before and after a split.** The refactor was checked by comparing the CSS rule by rule (128 of the dashboard's 143 rules byte-identical, the rest the deliberate merges), by screenshots of the same states, and by pulling a stray colour into each kind of component to see the colour test fail.

What the split changed on screen, on purpose: the logo mark is 40 px on both pages (was 42 on the call page), the brand subtitle is "Voice ordering" on both (so the shop name sits beside the logo on a phone), the call page's cards use the same panel as the dashboard's, and empty states use one padding.

Adding a component: write `components/<page or shared>/<name>.{html,css,js}`, add its `{{include:...}}` line to the page, and run `python -m pytest tests/test_webpage.py` and `node --test tests/web/`. See the page output with `python -m dukaan_dost.webpage index` or `dashboard`.

## The call page
`dukaan_dost/web/index.html` (a template; components under `components/call/`). A call screen on the left, what the caller needs beside it. The shared palette below, with a matching dark theme; icons are inline SVG because the pages load nothing from outside.
- **The call screen:** a status chip with the call timer, the language heard so far, a shop mark, a large state line, a waveform, and the controls. **Start call** becomes **End call**; **Mute** appears during a call.
- **States** (worked out by the page itself from what it is doing): listening (the waveform follows the caller's own microphone), thinking (after the caller's words arrive, until the first reply clip; given up after 12 s because not every turn gets a spoken reply), speaking (the waveform follows the agent's voice), muted, ended.
- **Live transcript:** what the caller said and what the agent said, one bubble per reply. A reply cut off by the caller is marked "(interrupted)". The agent's text is shown when it is queued for speech, a moment before it is heard.
- **Current order:** read-only (the caller changes the order by voice; totals are computed in code). It shows "coming soon" until the agent sends `order` messages, which waits for the order state (build step 8, DEC-006).
- **Plain messages** for the common failures: a page that is not `localhost` or `https` (no microphone), permission denied, the agent not running, another call in progress.
- **Not taken from the mockup:** a speaker button (meaningless in a browser tab), a language picker (Prisma detects the language and the app locks it for the call), +/- buttons on order lines.
- **New protocol messages**, server to page: `user` (`text`, `lang`), `agent` (`reply`, `text`), `order` (`items`, `total`). Sent through `Transport.send_event`, which never blocks the call. Listed at the top of `transport_websocket.py`.
- **Everything the server sends is shown as text, never as HTML**, and a Node test fails if `innerHTML` and friends appear.
- Needs `localhost` or `https`. **Still not tried with a real microphone in a real browser** (B-08). Checked as a render in headless Chrome at 1280, 700 and 390 px wide, light and dark, with the states driven by script: no horizontal overflow.

## The shopkeeper dashboard
`dukaan_dost/web/dashboard.html` (a template; components under `components/dashboard/`), data from `/s/<shop>/dashboard/data`. Redesigned 2026-11-02 to match the call page (same palette, light and dark).
- **Side menu** (a wrapped row on a phone): Dashboard, Orders, Credit book (udhaar), Loan enquiries. **Stock & prices** and **Reports** are shown as "soon". The sections are views of one page, switched by the address fragment (`#orders`), so the data keeps polling.
- **Dashboard view:** a greeting, then three tiles with icons: sales today (the hero) and orders today (each against yesterday up to the same time; no percentage from a zero), and owed on credit. What needs the shopkeeper is the count in the heading of the "Needs your attention" panel, not a tile of its own, because a tile repeated what that panel lists (one home per fact). Below: the five latest orders, the needs-attention list, a 7-day sales chart, and **Quick actions** (add stock, add customer or credit, today's report), which are disabled and marked "soon" because the server cannot take writes yet (DEC-034).
- **Needs attention** is worked out in the page: incomplete orders, credit-pending orders, and customers at 90% or more of their credit limit. Stock levels are not included: the stock list only says in stock or out, with no counts.
- **Orders / Credit book / Loan enquiries views:** the full lists; an order opens to its items, delivery and credit balance before and after.
- **Live:** it polls every 3 seconds; the top bar says whether a call is up (neutral grey when none) and "Connection lost" if the server stops answering.
- **Safe by construction:** the page builds everything from text nodes, never HTML strings, and loads nothing from outside; Node tests fail on `innerHTML` and friends and on any address in the script. The server sends a strict content security policy.
- **New data from the server:** `summary.orders_yesterday`, `summary.sales_yesterday` and `trend` (seven days, oldest first; incomplete orders excluded from sales).
- **Checked** in headless Chrome at 1280, 1100, 390 and 360 px, light and dark: no horizontal overflow. Not tried on a real phone.
- **Shows demo data only** until the agent writes real orders (B-11). Demo data is marked "made-up".

**See it without keys:** `python -m dukaan_dost.preview` serves just the dashboard with a made-up shop (password `1111`) from a temporary folder.

## Admin dashboard (planned)
List shops and their status; add a shop from a template and set its PIN; see each shop's errors and mark them solved; edit a shop's prompt and stock list. It needs writes, which the server's HTTP layer can't take as request bodies, so the page will talk over a WebSocket with JSON commands (no new dependency).

## Rules for all of them
- Synthetic data only in screenshots and the video (R-2).
- Anything a caller or shopkeeper sees ships as a build.
- Readable on a phone screen.
