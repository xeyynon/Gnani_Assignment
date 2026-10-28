# Frontend

Two pages. The call page exists; the order viewer is planned.

## The call page (built, Build 1002)
`dukaan_dost/web/index.html`, served by the agent at `/`. It is the "phone".
- **Start call** asks for the microphone (with the browser's echo cancellation, noise suppression and gain control switched on), opens the WebSocket, and streams the microphone as 16 kHz mono PCM. An AudioWorklet resamples from the browser's own rate (44.1 or 48 kHz).
- It plays each sentence the agent sends, one clip at a time, and tells the server when a clip finished or was stopped.
- **Hang up** closes the socket. A level bar shows the microphone, and a pill shows whether the agent is speaking.
- It needs `localhost` or `https` for the microphone, no libraries, and no network access other than its own server.
- **Untested in a real browser so far.** The server protocol and the resampler are tested; the page itself is not (B-08).

## Order viewer (planned)
- **What it shows:** the orders in `orders/*.json`, newest first. Each has the time, language, items with quantities and prices, the total, delivery and payment choices, and a status (confirmed or incomplete).
- **Why it exists:** the 60-second demo has to end with the order summary on screen.
- **Simplest version:** a static `orders/index.html` regenerated each time an order is written, so nothing extra runs. If time allows, a small page on the same server that refreshes while the call ends.

## Rules for both
- Synthetic orders only in screenshots and the video (R-2).
- Anything a caller or shopkeeper sees ships as a build.
- Keep them readable on a phone screen.
