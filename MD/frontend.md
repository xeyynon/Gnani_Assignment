# Frontend

Three pages, all served by the agent on one port. Two exist; the admin one is planned.

| Page | Address | Who | Status |
|---|---|---|---|
| Call page | `/s/<shop>/` (and `/` for the default shop) | The caller | Built (Build 1002) |
| Shopkeeper dashboard | `/s/<shop>/dashboard` | The shop's owner, with the shop's PIN | Built (Build 1003) |
| Admin dashboard | `/admin` | You, with the admin password | Planned (DEC-034) |

## The call page
`dukaan_dost/web/index.html`. A call screen on the left, what the caller needs beside it. Light, muted palette (warm off-white, one soft green) with a matching dark theme; icons are inline SVG because the pages load nothing from outside.
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
`dukaan_dost/web/dashboard.html`, data from `/s/<shop>/dashboard/data`. Redesigned 2026-11-02 to match the call page (same calm palette, light and dark).
- **Side menu** (a wrapped row on a phone): Dashboard, Orders, Credit book (udhaar), Loan enquiries. **Stock & prices** and **Reports** are shown as "soon". The sections are views of one page, switched by the address fragment (`#orders`), so the data keeps polling.
- **Dashboard view:** a greeting, then four tiles with icons: orders today and sales today (each against yesterday; no percentage from a zero), owed on credit, and what needs the shopkeeper. Below: the five latest orders, the needs-attention list, a 7-day sales chart, and **Quick actions** (add stock, add customer or credit, today's report), which are disabled and marked "soon" because the server cannot take writes yet (DEC-034).
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
