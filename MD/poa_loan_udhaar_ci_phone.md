# Plan of action: loan guidance, udhaar, CI, phone and several callers

**Written 2026-11-03.** Covers the four items still marked as calculator-only, not built, unseen, and later. It fits inside the main plan ([poa_final_week.md](poa_final_week.md)) and does not replace it: the evaluation, the README, the real-microphone test, the videos and the posts stay first.

## 0. Order and why
| # | Item | Do it | Why in this place |
|---|---|---|---|
| 1 | **GitHub CI** | now | Costs no model tokens, can break the submission silently, and is cheap to check |
| 2 | **Loan guidance on the call** | Nov 3 to 4 | Deterministic (exact right answers, a clean evaluation), small, and a second thing to show in the demo |
| 3 | **Udhaar credit book** | Nov 4 to 5 | Bigger and touches the order flow; the stated first thing to cut |
| 4 | **Phone number and several callers** | decide on Nov 5; build only if everything above is done and KYC has cleared | Depends on outside parties and a rewrite of the main file |

**Token budget.** Groq allows about one full evaluation run per model per day (B-33). All four items are therefore built and tested with scripted model answers (free), and each gets at most one short live check. The evaluation runs of the main plan have first call on the quota.

**Cut rule.** If the main plan slips, drop in this order: 4, then 3, then 2. Item 1 is never dropped.

---

## 1. GitHub CI and release
**Where it is.** `.github/workflows/ci.yml` (tests on Ubuntu 3.10 and 3.12 and Windows 3.12, ruff, repo hygiene, page tests, a container build) and `release.yml` (on a `build-*` tag: a GitHub Release from the build report, and an image). Nobody has seen a run. The repository is private, so a run cannot be read from this machine (checked: the public API answers 404).

**What can be done without seeing GitHub.** Reproduce the run locally in a clean environment built only from `requirements.txt`, which finds most real failures (missing dependencies, a test that only passes with local files, lint errors, Windows-only code).

| Task | Detail | Status |
|---|---|---|
| 1.1 | `scripts/ci_local.py`: clean venv, install, pytest, ruff, a static check that the code needs no newer Python than 3.10 (CI runs 3.10, which is not installed here), hygiene, page tests, container build and import | ✅ written 2026-11-03 |
| 1.2 | Run it; fix every failure it finds | ✅ 2026-11-03: in a clean venv all 779 Python tests pass, ruff is clean, the repo and doc checks pass, all 93 page tests pass, the code needs only Python 3.9 so the 3.10 job should pass, and every pinned requirement resolves to Linux wheels for Python 3.10 and 3.12. Not run: the container build (the Docker daemon is off here) and the Ubuntu jobs themselves. Found and fixed one stray test warning |
| 1.3 | Surya opens the Actions tab after the next push and reports red jobs | ⬜ needs Surya |
| 1.4 | Set the `BANNED_TERMS` repository variable (Settings, Secrets and variables, Actions, Variables) so the customer-name check runs on GitHub | ⬜ needs Surya |
| 1.5 | After a green run: protect `main` (require CI to pass), add a licence | ⬜ needs Surya's choice |

**What reading the workflows showed.**
- `ci.yml` runs on pushes to `main` and on pull requests only. Work pushed to another branch (the recent pushes went to `admin-dark-ui`) starts nothing until a pull request is opened or the branch is merged. So an empty Actions tab for those pushes is expected, not a failure.
- `release.yml` runs when a `build-*` tag is pushed, and it first runs all of `ci.yml`. The `build-100x` tags already pushed will have started it, so the Actions tab should show those runs. Read them first.
- The container build needs the Docker daemon: start Docker Desktop and run `python scripts/ci_local.py` to include it.

**Known unknowns:** the Python 3.10 job (checked statically only), the container build if Docker is not running here, and whether the workflow's pinned action versions still exist.
**Done when:** `ci_local.py` ends with every step `ok`, and the first GitHub run is green or its failures are fixed.

---

## 2. Loan guidance on the call (Udyami Sahayak)
**Where it is.** `loan_calculator.py` is correct and tested (it reproduces the problem statement's example: ₹1,00,000 gives an EMI of ₹15,438 over 78 months). Nothing connects it to a call. The scheme figures are indicative (DEC-028), and the agent must say so.

**Design (same principle as orders: the model reads, the code decides and speaks).**
1. **Routing, in code.** A keyword check (`loan_intent`) in English, Hindi, Telugu and Hinglish (loan, लोन, कर्ज, ब्याज, వడ్డీ, EMI, "start a business") switches the call into loan mode. Keywords cost no tokens and a missed word falls back to the order flow. Telugu అప్పు is deliberately not a trigger: it means credit, which is udhaar. Loan mode lasts for the rest of the call.
2. **A short model prompt** (no catalogue, about a quarter of an order turn's tokens). The model returns one JSON object: the amount in rupees as digits, whether the caller meant their own money (margin) or the whole project cost, the kind of business, the place.
3. **The code does the rest.** Project cost is margin divided by 0.10 and the loan up to 90 percent of it, then the scheme, rate, moratorium and instalment, all from `loan_calculator.quote()`.
4. **The code speaks the answer** in the caller's language from templates, reading back the amount it heard: "I heard ₹X of your own money, so a project of about ₹Y. The Micro Finance scheme could lend up to ₹Z at 6.5 percent. After 3 months' grace, about ₹E a month for N months. These figures are approximate; tell me if I misheard the amount." A correction replaces the quote. If no amount was understood the code asks for it; above ₹50 lakh it says that is outside the scheme.
5. **The record** goes to `orders/<shop>/loan_<id>.json` (format in `store.py`), which the dashboard already shows.

| Task | Detail | Tests | Status |
|---|---|---|---|
| 2.1 | `loan_session.py`: state, validation, the quote, the spoken text in three languages, the record | free | ✅ 2026-11-03 |
| 2.2 | `loan_turn.py`: prompt, schema, parsing; keyword router | free | ✅ 2026-11-03 |
| 2.3 | Conversation manager and `app.py` hooks (a loan state per call; saved at call end) | free | ✅ 2026-11-03, 75 tests |
| 2.4 | Check how Timbre reads lakh-style numbers (a round trip, no model tokens) | live, small | ✅ 2026-11-03: it misreads six and seven digit numbers in Hindi and Telugu (B-37); lakh words are read correctly, so amounts from a lakh up are spoken that way |
| 2.5 | Four scripted loan calls with expected quotes; one live run | live, small | 🟡 scripts written (`credit_loans.json`) and 4 live cases checked by hand; the scored run waits for model tokens |
| 2.6 | Figures re-checked against the official scheme documents (the brief's numbers are from an SIH problem statement) | needs Surya | ⬜ |

**Risks.** The model mishears an amount (the same risk as quantities: the read-back lets the caller correct); the instalment rule is an assumption (DEC-028), stated aloud as approximate.
**Done when:** a scripted Hindi, Telugu, English and Hinglish loan call each produce the quote the calculator gives for the amount said, the record appears on the dashboard, and the figures are labelled approximate everywhere they are spoken or shown.

---

## 3. Udhaar credit book
**Where it is.** Credit orders are saved as `credit_pending` with no balance. The ledger file format exists in `store.py` and the dashboard reads it (demo data only).

**Design.**
1. **A synthetic customer list** `shops/<shop>/customers.json`: about 15 made-up customers with their names in English, Hindi and Telugu, a credit limit and an opening balance.
2. **A credit book** (`credit.py`) over `orders/<shop>/ledger.json`: find a customer by name (tolerant of spelling and script, ambiguous means unknown), balance, limit check, and an entry per order. The ledger is created from the customer list the first time.
3. **In the order flow** (code decides, as with totals):
   - Caller chooses udhaar and no name is known: the code asks for the name.
   - Known customer, within the limit: the code says the current balance, this order and the new balance; the order is saved with `balance_before` and `balance_after` and the ledger is updated when the call ends.
   - Over the limit: the code says so and offers cash or UPI; the payment is not credit.
   - Unknown name: saved as `credit_pending` for the shopkeeper to confirm (today's behaviour), and the caller is told that.
4. **Balance enquiry**: "how much do I owe?" The model sets a flag and the name; the code reads the balance from the ledger and speaks it.
5. **Not in scope:** promise-to-pay dates, reminders, outbound calls.

| Task | Detail | Tests | Status |
|---|---|---|---|
| 3.1 | `customers.json` with 15 synthetic customers | free | ✅ 2026-11-03 (names need a native check) |
| 3.2 | `credit.py` and its tests (matching, limits, atomic ledger write) | free | ✅ 2026-11-03 |
| 3.3 | Order flow changes: ask for the name, the three outcomes, the balance enquiry | free | ✅ 2026-11-03 |
| 3.4 | Spoken sentences in three languages | free | ✅ 2026-11-03 |
| 3.5 | Four scripted calls (approved, over the limit, unknown name, balance enquiry) and one live run | live, small | 🟡 scripts written; the live run was cut off by the model's daily limit after the first step (B-33) |
| 3.6 | Dashboard shows real balances | free | ✅ 2026-11-03: a snapshot test reads the ledger the agent wrote; not yet seen in the browser |

**Risks.** A mis-heard name gives the wrong customer (mitigation: ambiguous or low-similarity means unknown, never guessed); the order prompt grows by two fields (about 100 tokens a turn).
**Cut rule:** if Nov 5 arrives without 3.1 to 3.4 working, leave credit as `credit_pending` and describe the ledger as future work (DEC-026).
**Done when:** the four scenarios behave as above in tests, the ledger and the order file agree, and one live call shows the balance on the dashboard.

---

## 4. A real phone number, and several callers at once
Two separate jobs, both optional for the submission.

### 4a. A phone number
**Facts found (2026-11-03, search results, to be confirmed with the providers):**
- **Exotel** streams live call audio to a WebSocket. Its guide says streaming access requires completed KYC and a confirmation from Exotel's compliance team, and the Stream applet is enabled by an email to support. No turnaround time is published. ([Exotel AgentStream](https://developer.exotel.com/docs/agentstream/connect-voice-ai), [quick guide](https://support.exotel.com/support/solutions/articles/3000132268-quick-guide-to-get-started-with-exotel-streaming-services))
- **Twilio** streams call audio over WebSockets (Media Streams, one bidirectional stream per call) and requires a regulatory bundle (end-user details and documents) before it will issue a number in regulated countries. I could not read India's exact document list. ([Twilio regulatory guidelines](https://www.twilio.com/en-us/guidelines/in/regulatory), [Media Streams](https://www.twilio.com/docs/voice/media-streams.md))
- Phone audio is 8 kHz mu-law; our pipeline is 16 kHz. Plain resampling is the safe conversion (method M8 in [research_papers.md](research_papers.md)); Timbre can also emit 8 kHz mu-law directly.

**Conclusion.** The slow part is the provider's approval, not our code, and neither approval has a promised time. So:
| Task | Detail | When |
|---|---|---|
| 4a.1 | Surya starts KYC with one provider now (it costs nothing and runs in the background) | now, needs Surya |
| 4a.2 | A `TelephonyTransport` that speaks the provider's WebSocket messages, converts mu-law 8 kHz to 16 kHz PCM and back, and maps a call to a session; developed and tested against a fake provider (no account needed) | ✅ 2026-11-03 (DEC-046, 31 tests; never run against a real provider, B-39) |
| 4a.3 | A public HTTPS address for the server (a tunnel is enough for a demo) | when 4a.2 is done |
| 4a.4 | Real calls, a noisy 8 kHz evaluation run, the demo video made from a real phone call | only if KYC has cleared by Nov 7 |

**Decision point: Nov 5.** If KYC has not cleared, the demo is the browser call and this item moves to "future work". A browser call is a legitimate demo of the same pipeline.

### 4b. Several callers at once
**Sizing.** `app.py` is 3,437 lines written for one call: about 30 module-level variables, queues and events (call generation, history, language lock, playback flags, the current order) and five threads that all assume a single call. Several callers means turning that into one object per call, with its own threads or tasks, while sharing the model client, the shop data and the speech connections. That is a rewrite of the main file with a high chance of new bugs, two to three days of careful work plus new tests, and it also needs Gnani's concurrent-session limit (still unmeasured: `gnani_smoke_test.py concurrency`) and more model quota than the account has.

**Recommendation: do not build it for the submission.** The honest options, in order of cost:
1. **Say so:** one call at a time per agent process, "busy" for the second caller (the call page already shows a busy message). A kirana shop's phone is rarely on two calls at once.
2. **Several processes:** run one agent per port and let the call page pick a free one. No code change in the pipeline; each process keeps its own state. Needs only a small router and more provider quota.
3. **The rewrite**, as future work, with the design above.

| Task | Detail | When |
|---|---|---|
| 4b.1 | Measure Gnani's real concurrent-session limit (`python scripts/gnani_smoke_test.py concurrency`) and record it | ✅ 2026-11-03: 8 sessions open at once, none refused (higher untested) |
| 4b.2 | Write the per-call state inventory and the rewrite design into `MD/architecture.md` as future work | ✅ 2026-11-03 |

---

## 5. Schedule
| Day | Items | Done when |
|---|---|---|
| **Nov 3** | 1.2 (fix what CI shows) · 2.1 to 2.3 (loan, free tests) · 4a.1 and 4b.1 asked for / run | `ci_local.py` all `ok`; loan flow passes scripted tests |
| **Nov 4** | 2.4 and 2.5 (loan live check) · 3.1 to 3.4 (udhaar, free tests) | Loan call works live; udhaar passes scripted tests |
| **Nov 5** | 3.5, 3.6 · decision on 4a · 1.3 | Udhaar demo-able; phone decision made |
| **Nov 6 to 7** | Only what remains of 4a if KYC cleared; 4b.2; fixes from the evaluation | |
| **Nov 8** | Nothing new. Final checks | |

## 6. What I need from Surya
1. Open the Actions tab on GitHub after the next push and tell me which jobs are red (1.3), and set the `BANNED_TERMS` variable (1.4).
2. Start KYC with Exotel or Twilio today if a phone number is wanted at all (4a.1).
3. Confirm the scheme figures against the official documents, or tell me they may stay "approximate" (2.6).
4. Read the synthetic customer names when they exist (3.1).
