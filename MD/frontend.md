# Frontend

Three pages, all served by the agent on one port. Two exist; the admin one is planned.

| Page | Address | Who | Status |
|---|---|---|---|
| Call page | `/s/<shop>/` (and `/` for the default shop) | The caller | Built (Build 1002) |
| Shopkeeper dashboard | `/s/<shop>/dashboard` | The shop's owner, with the shop's PIN | Built (Build 1003) |
| Admin dashboard | `/admin` | You, with the admin password | Planned (DEC-034) |

## The call page
`dukaan_dost/web/index.html`. **Start call** asks for the microphone (echo cancellation, noise suppression and gain control on), opens `/s/<shop>/ws`, and streams the microphone as 16 kHz mono PCM; an AudioWorklet resamples from the browser's own rate. It plays each sentence the agent sends and tells the server when a clip finished or was stopped. It shows the shop's name. Needs `localhost` or `https`. **The page and the microphone path have not been tried in a real browser yet** (B-08).

## The shopkeeper dashboard
`dukaan_dost/web/dashboard.html`, data from `/s/<shop>/dashboard/data`.
- **Four numbers first:** orders today, sales today (incomplete orders excluded), owed on credit, and what needs the shopkeeper (credit pending or incomplete).
- **Orders**, newest first: customer, items, time, a coloured status pill, payment, total; tap one for the items, delivery and the credit balance before and after. New orders are highlighted briefly.
- **Credit book (udhaar):** each customer's balance against their limit, red above 90%, with the promised date or last purchase.
- **Loan enquiries:** margin, project cost, loan, scheme, instalment and months, tagged "indicative".
- **Live:** it polls every 3 seconds and says "Connection lost" if the server stops answering. Dark and light themes follow the device.
- **Safe by construction:** the page builds everything from text nodes, never HTML strings, because order data contains text a caller chose; a Node test fails if `innerHTML` and friends appear. The server sends a strict content security policy.
- **Checked** in headless Chrome with demo data at 1200, 1100 (light), 400, 390 and 360 px wide: no horizontal overflow, numbers match the calculator.
- **Shows demo data only** until the agent writes real orders (B-11). Demo data is marked "made-up".

## Admin dashboard (planned)
List shops and their status; add a shop from a template and set its PIN; see each shop's errors and mark them solved; edit a shop's prompt and stock list. It needs writes, which the server's HTTP layer can't take as request bodies, so the page will talk over a WebSocket with JSON commands (no new dependency).

## Rules for all of them
- Synthetic data only in screenshots and the video (R-2).
- Anything a caller or shopkeeper sees ships as a build.
- Readable on a phone screen.
