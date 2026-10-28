# Idea research: what to build for the challenge

**Researched 2026-10-28** from the contest page, Gnani's blog and website, and the competing entries already public on GitHub. The question: is Dukaan Dost (a kirana phone-order agent) the right entry, or is there something better to build on the same pipeline?

## 1. What Gnani is asking for
- **An open brief:** "Build any working application on Gnani AI's models or APIs, show it in public, and explain how you built it."
- **Their four example ideas** (from gnani.ai/internship):
  1. A Kannada voice helpline reading crop and weather advisories to farmers (Main Character, Real Deal)
  2. **A Hinglish voice assistant that takes phone orders for a neighbourhood kirana store (Mixed Vibes, Real Deal)**, which is our idea
  3. A call summariser that holds up on noisy phone audio, tested on synthetic calls (Noise Canceller)
  4. A Tamil voice tutor that quizzes students out loud (Jugaad Genius)
- **What the blog stresses:** "start with an Indian problem, an Indian language and real Indian audio", and **"A demo that fakes a result will cost you more than one that shows an honest limitation."**
- **What Gnani sells** (gnani.ai): voice agents, call analytics, voice biometrics and agent assist, for **BFSI (collections, KYC, onboarding), customer support and lead qualification**. Customers include Equitas SFB, Bank of Baroda, Crompton and matrimony.com. Its claims: "14M+ hours of telephonic audio", "#1 on 8 of 9 Indian languages on Kathbath Noisy 8kHz". **Gnani's whole business is phone calls.**

## 2. The competition so far (public GitHub repos, 2026-10-28)
| Entry | What | How it takes audio | Notes |
|---|---|---|---|
| Bolkar Order Karo (motalib6) | **Hinglish kirana voice ordering**, shopkeeper dashboard | **Browser or mic upload**, no telephony | Prisma v2.5, Timbre v2.5; no LLM (keyword matching); 20/20 on *parser* tests only; mock mode |
| KisanSetu (aniket25042005) | Farmer voice desk | Web | Prisma and Timbre v2.5 |
| Dhwani Desk (Pranav-0710) | Kannada civic-complaint helpline, supervisor console | "Phone-quality" 8 kHz audio; team of two | Prisma and Timbre v2.5, a fine-tuned local classifier; strong on Main Character |
| Savdhaan (tejaspatel2255) | Live scam-call warning | Browser (mic, file, replay) | Prisma v2.5, Timbre v3.0; eval on perfect transcripts only |
| Scam Sentinel (Hrishvith) | Scam-call detector | — | Second scam entry |
| gnani-voice-ops-line | Hinglish reporting line for field crews | — | Mock provider; live test pending |
| Bolo (satyabrata-mishra) | Multilingual form filling | — | Uses Evon v3.3 |
| ClientReady | Voice coaching for freelancers | — | |
| boli-zero | Bhojpuri into a Hindi voice stack | — | Experiment |

**Patterns:**
- Almost everyone is on **Prisma v2.5 and Timbre v2.5**.
- Almost everyone takes audio from a **browser or uploaded files**. None of the repos shows a **real phone call** taking a real order.
- Evaluations, where they exist, test the **text parser**, not speech end to end, and not on noisy phone audio.
- **Kirana, farmers and scams are already taken**, and kirana and farmers are Gnani's own examples, so expect several more of each.

## 3. Our unfair advantages
1. **A real phone line.** You dial a real number and a Raspberry Pi answers over Bluetooth. Nobody else shows this, and it's Gnani's home turf.
2. **A production-hardened call pipeline:** barge-in, echo handling, per-call language lock, call isolation, tuned on real calls (upstream, July–August 2026).
3. **Telugu** as a first-class language (Main Character), which none of the visible entries covers.
4. **Prisma v3.0** (auto language, `codemix`, keyterms, `commit`), released 2026-10-22; most entries are on v2.5.
5. **Measured evaluation on noisy phone audio**, end to end (STT, then order accuracy, then latency), which nobody shows yet.

## 4. Options
All of them reuse the same pipeline. Switching domain costs mainly `companies/<name>/` (prompt and knowledge) plus the domain logic (order state, ledger and so on).

| # | Idea | Awards in reach | Crowding | Extra work over the base | Fit with Gnani's business |
|---|---|---|---|---|---|
| **A** | **Dukaan Dost as planned:** kirana phone orders in Telugu, Hindi and Hinglish, on a real phone line | Real Deal, Mixed Vibes, Main Character, Noise Canceller, Solo Ninja, Demo Day | **High.** It's a Gnani example, and one entry already exists | Low (as planned) | Medium (a voice agent) |
| **B** | **Dukaan Dost + udhaar khata:** the same agent also records credit ("likh lo, month-end pe dunga"), tells the caller their outstanding balance, and the shop gets a daily ledger | All of A, plus a clearer "real" story; Jugaad possible | Medium: the kirana base is crowded, the credit ledger isn't | Low–medium: a ledger next to the order, more prompt rules | **High.** A small-scale collections and BFSI flavour |
| **C** | **Payment-reminder caller for SHG and microfinance loans** in Telugu and Hindi: polite EMI reminders, records the promise-to-pay date, answers "how much is due" | Real Deal, Main Character, Noise Canceller; Jugaad (outbound calls from a Pi) | Low | **High**: outbound dialling over Bluetooth (AT commands or oFono) is new and risky; debt-collection tone is sensitive | **Very high** (this *is* Gnani's core business) |
| **D** | **Clinic or PHC appointment line in Telugu:** book, move or cancel; the clinic gets a day sheet | Real Deal (rural health), Main Character | Low–medium | Low–medium | Medium |
| **E** | **Noisy-call summariser** (Gnani example 3) on our own phone-line recordings | Noise Canceller | Medium | Medium | High (call analytics), but no live agent, which wastes our telephony edge |

## 5. Recommendation: B, "Dukaan Dost + udhaar khata"
- **It keeps everything already planned and written** (docs, decisions, the pipeline). With 13 days left, a pivot to C's outbound dialling isn't worth the risk.
- **It escapes the crowd without leaving Gnani's example.** "Takes phone orders" matches what judges expect; **"and keeps the shop's credit book by phone, in Telugu"** is something no other entry does, and it's how real kiranas run (most regulars buy on credit).
- **It speaks to Gnani's business:** balance enquiries and promise-to-pay are what their collections customers buy, at kirana scale.
- **The demo writes itself:** a real phone call, a Hinglish order, an interruption, "isko udhaar mein likh dena", the total read back, then the shopkeeper's screen showing the order **and** the updated credit balance.
- **Differentiators, in order of importance for the judges:**
  1. a real phone call, not a browser
  2. Telugu plus Hinglish on Prisma v3.0
  3. measured, end-to-end results on noisy phone audio
  4. the credit ledger

**Scope guard:** the udhaar ledger is a small add-on (a per-customer balance, identified by a name the caller says, with synthetic customers only). If time gets tight it's the first thing cut, and the entry is still plan A.

## Sources
- Contest page: https://www.gnani.ai/internship
- Gnani blog: https://www.gnani.ai/resources/blogs/great-indian-ai-internship-challenge-2026
- Gnani website: https://www.gnani.ai
- Competing entries: https://github.com/motalib6/gnani-kirana-voice-agent, https://github.com/aniket25042005/kisan_setu_gnani_ai_challenge, https://github.com/Pranav-0710/dhwani-desk, https://github.com/tejaspatel2255/savdhaan-gnani, https://github.com/Hrishvith/Scam-Sentinel, https://github.com/Sivadheeraj5356/gnani-voice-ops-line, https://github.com/satyabrata-mishra/Gnani-AI-Hackathon, https://github.com/Mandalorian7773/ClientReady, https://github.com/sameer261h/boli-zero
