# Frontend

**Status: planned, not built.** Dukaan Dost's main interface is the phone call. The only screen is an optional order viewer for the shopkeeper, and for the demo video (build step 8).

## Order viewer (planned)
- **What it shows:** the orders in `orders/*.json`, newest first. Each one has the time, language, items with quantities and prices, the total, delivery and payment choices, and a status (confirmed or incomplete).
- **Why it exists:** the 60-second demo has to end with the order summary on screen. A shopkeeper would glance at it between customers.
- **Simplest version:** a static `orders/index.html` regenerated each time an order is written. No server, so nothing extra to run on the Pi.
- **If time allows:** a tiny Flask page on the Pi's LAN address, auto-refreshing, so a new order appears while the call ends.

## Rules for it
- Synthetic orders only in screenshots and the video (R-2).
- It's a build when it ships (a shopkeeper sees it). Record it in a build report.
- Keep it readable on a phone: the shopkeeper's phone is the likely screen.
