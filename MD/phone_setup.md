# Setting up the phone line: a customer calls a number and orders

**Written 2026-11-06.** This is the checklist for connecting a real phone number to the agent (DEC-046). The transport in [transport_telephony.py](../dukaan_dost/transport_telephony.py) is tested only against a stand-in provider (B-39), so until step 8 has passed with a real call, nothing about the phone line may appear in the README, the posts or the video (rule R-5).

```
Customer dials the shop's number
   -> provider (Exotel or Twilio) answers, opens a WebSocket to our public address
   -> the agent's pipeline: Prisma -> Groq -> order code -> Timbre
   -> reply audio goes back through the provider to the customer
```
The agent never dials out. A normal SIM cannot be answered by software: the provider gives a virtual number, and the shop's own mobile can forward calls to it.

## 1. Choose the provider and start the paperwork (Surya; the slow part)
| | Exotel (recommended for an Indian number) | Twilio |
|---|---|---|
| Streaming | Voicebot or Stream applet, gated: KYC must be complete and Exotel enables the applet on request (an email to support naming the Account SID). Their guide: <https://support.exotel.com/support/solutions/articles/3000132268-quick-guide-to-get-started-with-exotel-streaming-services> | Media Streams, no gate beyond the number |
| Indian number | Issued by Exotel after KYC | Needs an approved regulatory bundle first (up to two business days after submission): <https://www.twilio.com/en-us/guidelines/in/regulatory> |
| Not known | Whether a trial account may use streaming: ask them | Whether a trial account may use an Indian number with Media Streams: ask them |

Neither publishes a turnaround for the whole process. **Decision point: if streaming is not enabled by Nov 8, the phone line comes out of the demo and the browser call is the demo.**

Email for Exotel support (subject: `Enable Voicebot/Stream applet - Account SID <your SID>`):
> Please enable the Voicebot/Stream applet (AgentStream) on my account. Use: inbound calls to a virtual number stream audio over WebSocket to my own server for a voice-agent project. Please confirm whether a trial account can use it and what KYC is still pending.

### 1b. Exotel, step by step (facts read from Exotel's pages on 2026-11-06)
1. Create an Exotel account and pick the instance: **Mumbai (Veeno)** is the one they recommend for Indian customers and is required for WebSocket plus SIP trunking; Singapore is the default for most other uses.
2. Submit KYC through standard onboarding. Streaming is approved by their compliance team together with the KYC; the two can run in parallel.
3. Email hello@exotel.com, subject `Enable Stream/Voicebot Applet for <Account SID>`, with a short use-case note; copy your Account Director or Customer Success Manager, or the customer-happiness team will add them. Source: [quick guide](https://support.exotel.com/support/solutions/articles/3000132268-quick-guide-to-get-started-with-exotel-streaming-services).
4. Get an ExoPhone (the virtual number) from Exotel.
5. In the App Bazaar, create a flow for inbound calls and add the **Voicebot** applet (optionally a Play applet before it for a greeting, and a Passthru applet after it so Exotel reports call metadata and the disconnect). Set its fields ([applet page](https://developer.exotel.com/docs/agentstream/stream-voicebot-applet)):
   - **URL**: `wss://<tunnel host>/telephony/exotel`
   - **Sample Rate**: 16000 (the default is 8000; this agent accepts 8000, 16000 and 24000)
   - **Custom Parameters**: up to 3 key-value pairs, 256 characters in all: `token=<TELEPHONY_TOKEN>` and `shop=dukaan_dost`. They reach us in the start event as `custom_parameters`, which the agent reads.
   - Authentication alternatives: Basic Auth in the URL (`wss://<key>:<token>@host/path`, sent as an `Authorization` header) or IP allow-listing through Exotel. This agent checks `TELEPHONY_TOKEN`, not these.
6. Attach the flow to the ExoPhone in the dashboard.

**Seen in a real trial account on 2026-11-06:** the flow editor (App Bazaar, "Installed Apps", Custom Apps, Create) lists **Voicebot** and **Stream** among its Voice Applets, with no sign of a gate on a trial account. The Voicebot applet asks for one URL (a `http(s)` endpoint, or a `ws(s)` address typed straight in), a "Record this?" box, an "Encrypt DTMF?" box and a Next applet. Its own text says custom parameters may total 800 characters and number up to 25, which differs from the 3 pairs and 256 characters in the developer page above; the stricter limit is safe, and our `token` and `shop` fit in both. The account shows "Unverified Account" with 150 credits and a trial number; the dashboard bar asks for Verify Number, Complete KYC, make a payment and Get an ExoPhone. Whether a call from a stranger's phone to a trial number is allowed is not yet known. **Not documented on the pages I could read**: the exact click-path for this and for creating the flow. Ask Exotel support or your account manager for it when they enable the applet.

### 1c. Twilio, step by step (read on 2026-11-06)
1. Create a Twilio account. For an Indian number, create a **regulatory bundle** (country India, number type local or mobile, end-user type individual or business) with the documents Twilio asks for; the states are draft, pending review, in review, then approved or rejected. Which documents India needs is on [Twilio's India page](https://www.twilio.com/en-us/guidelines/in/regulatory): not readable in my fetch, so read it in the console.
2. Buy a number that uses the approved bundle. (Whether a trial account may do this: not found. Ask Twilio.)
3. Create a TwiML Bin with the markup in section 5 and set it as the number's "A call comes in" webhook. ([Stream reference](https://www.twilio.com/docs/voice/twiml/stream): `wss` only; **no query string on the url**; `<Parameter>` name and value together under 500 characters; the next TwiML runs only after your server closes the socket.)
4. Twilio needs the WebSocket reachable on **TCP 443** from any public address ([Media Streams](https://www.twilio.com/docs/voice/media-streams)); a tunnel provides that. A call can have one bidirectional stream.

## 2. Settings in `.env` (gitignored; never commit it)
```
AUDIO_TRANSPORT=telephony
TELEPHONY_TOKEN=<a secret of at least 16 characters>     # already generated on 2026-11-06; read it from .env
```
With `AUDIO_TRANSPORT=telephony` the browser call page still works on the same server. With no token, every phone call is refused and a warning is logged at start.

## 2b. The short way
`python scripts/phone_demo.py` does steps 3 and 4 in one command: it starts the agent in phone mode (port 8766), starts `cloudflared` and reads the tunnel address it gets, prints the URL for the Voicebot applet (add your `TELEPHONY_TOKEN` after `token=`: the secret is never printed) and shows the call's `[PHONE]` and order lines. Ctrl+C stops both. The address changes at every start, so edit and save the applet's URL each time. `--no-tunnel` starts only the agent.

## 3. Start the agent
```
python -m dukaan_dost
```
Wait for `server listening on 127.0.0.1:8765` and, with a token set, no `[PHONE] TELEPHONY_TOKEN is missing` warning.

## 4. Give the provider a public address (a tunnel)
The provider connects to us, so the laptop needs an HTTPS/WSS address on the internet. Any tunnel that forwards WebSockets works, for example:
```
cloudflared tunnel --url http://127.0.0.1:8765
```
It prints an address like `https://something.trycloudflare.com`; the WebSocket address is the same with `wss://`. The address changes each time the tunnel restarts, so update the provider each time. Close the tunnel when you are not testing: anyone with the address and the token could place a call that spends Prisma, Timbre and Groq quota.

## 5. Point the provider at the agent
**Exotel** (Voicebot applet, in the call flow of the number): the WebSocket URL is
```
wss://<tunnel host>/telephony/exotel?sample-rate=16000&token=<TELEPHONY_TOKEN>&shop=dukaan_dost
```
**Twilio** (a TwiML Bin on the number's voice webhook):
```xml
<Response>
  <Connect>
    <Stream url="wss://<tunnel host>/telephony/twilio">
      <Parameter name="token" value="<TELEPHONY_TOKEN>"/>
      <Parameter name="shop" value="dukaan_dost"/>
    </Stream>
  </Connect>
</Response>
```
`shop` picks the shop; leave it out to use the default shop. The token in the Exotel URL can show up in the tunnel's logs, so use a token made only for this and change it afterwards.

## 6. The shop's own mobile number (optional)
Ask the mobile carrier to forward calls to the provider's virtual number (the carrier's conditional-forwarding code: when unanswered, busy or unreachable). Customers keep dialling the number they know.

## 7. What to watch in the agent's terminal during a call
- `[PHONE]` lines when the call starts and ends. The caller's number is never logged; if one ever appears, stop and fix it.
- `[PHONE] refused ... wrong or missing token`: the token in the provider differs from `.env`.
- A second call while one is going is closed as busy (one call at a time).
- A greeting you cannot hear, or a call that goes silent after the first reply, is the same class of fault as B-86: copy the log lines and report them.

## 8. The first real test (from a second phone, headset not needed)
1. Call the number. The greeting must play within a few seconds.
2. Order in Hinglish: "do kilo atta aur ek litre tel", "bas itna hi", "cash". Listen for the total and the confirmation.
3. Hang up, call again and order once more (the check for the call-boundary bugs).
4. Interrupt a reply once. The agent should stop and listen.
5. Open the shop dashboard: both orders must be listed.
6. Note anything that differs from the stand-in tests: the timing of the provider's `mark` replies, whether `clear` drops audio, how 8 kHz audio affects what Prisma hears (nothing measures this yet).

## 9. When it works
Record it as a result only after a saved run exists. Until then B-39 stays open and the README says the phone line is built and tested against a stand-in only.
