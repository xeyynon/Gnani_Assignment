# Build 1027: The agent reads the order back in the language the caller asks for, in any script

**Date:** 2026-11-10

## What changed
A caller can ask for the order again in another language, for example in Hindi: 'mera order Telugu mein dobara bolo'. The agent now recognises the language name whether it is written in Latin letters, Devanagari or Telugu script, and the order is read back by code in that language with the same total. More spoken read words are accepted (bata do, bolo, dohrao). On the Live call page the stray call counter is hidden and the Live or Offline pill shows again.

## Why
Prisma writes a Hindi sentence in Devanagari, so a request such as 'तेलुगु में' was not recognised and the order was read back in the call's own language. The demo call needed the Hindi request to produce a Telugu readback.

## How it was verified
tests/test_language_request.py (43 cases), test_dashboard and test_webpage, and the Node page tests pass. Shown on a real phone call on 2026-11-10 (the demo video): a Hinglish order, then a Hindi request, then the order read back in Telugu. Switching language inside one call is lightly tested: the scored runs use one language per call.

## What to improve next
Score a run that switches language inside a call. Have a native speaker check the Telugu and Hindi sentences.

<!-- Everything below is rebuilt from git by scripts/changelog.mjs. Edit above this line only. -->
## Files changed
- `M` dukaan_dost/app.py
- `M` dukaan_dost/web/components/live/screen.css
- `A` tests/test_language_request.py
