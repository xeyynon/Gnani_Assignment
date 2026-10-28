# Problem research: SIH and similar problem statements

**Researched 2026-10-28.** Companion to [idea_research.md](idea_research.md) (which compared our idea with other entries). This file mines official problem statements for real problems a Gnani-powered voice agent could solve, checks how real each problem is, and scores the options.

## How reliable this is
- **SIH 2026 text** comes from a third-party PDF mirror of the catalogue (226 problem statements: 172 software, 54 hardware), not sih.gov.in. Titles, organisations and descriptions below were read from it; **confirm on sih.gov.in before quoting a PS number publicly.**
- **Statistics** are mostly secondary (news, think-tank reports). Each is labelled with its source and caveat. Where I found nothing solid, it says so.
- Not found or not read: SIH 2025 PS 25074 (the Malayalam farmer assistant) exists only as a search snippet; PS 26173 (ISRO's iTantra) was seen by title only; the IndiaAI application-challenge PDF could not be downloaded; the Bhashini hackathon page returned nothing; no 2025 Kisan Call Centre volumes were found.

## 1. Voice-relevant SIH 2026 software problem statements
I searched all 342 pages of the catalogue for voice, speech, IVR, helpline, regional-language and conversational requirements.

| PS | Title (organisation) | Voice angle | Notes |
|---|---|---|---|
| **26097** | AI-driven voice assistant for livelihood mapping and NSQF-aligned skilling for SC communities (MoSJE) | **Voice is the whole point.** Conversational interview in regional languages and dialects; deployment via **IVR phone calls for feature phones**, WhatsApp voice notes, kiosks | Collects education, family trade, skills, mobility, wage vs self-employment; recommends NSQF trades |
| **26091** | Hyper-local business advisory and financial structuring assistant for rural micro-entrepreneurs (MoSJE) | Multilingual NLP assistant | **Deterministic finance rules**: margin money is 10% of project cost, loan is up to 90%. Project cost ≤ ₹1.40 lakh routes to the Micro Finance Scheme (6.5%, 3 years, 3-month moratorium); ₹1.40–50 lakh routes to the Term Loan Scheme (8%, 7 years, 6-month moratorium). Also asks for an EMI and moratorium schedule |
| **26068** | WeatherGPT: conversational AI for forecasts and alerts (IMD) | "Voice-enabled interaction for rural accessibility", multilingual | Farmers' crop-weather advisories are a named use case |
| **26128** | Early detection and management of livestock diseases (Maharashtra) | **IVR** among the channels; multilingual advisories; low-connectivity | Capture symptom and mortality reports from farmers, flag suspected outbreaks, dashboards for vets |
| **26133** | Accessibility of public healthcare in rural areas (Maharashtra) | Multilingual, low-connectivity; digital triage, queue and appointment management | Broad; voice not mandated |
| **26047** | Patient case-taking software (AIIA, Ministry of Ayush) | Spoken history-taking in Indian languages, **noisy hospital environment**, kiosk | Large: also needs OCR of prescriptions and ABDM integration |
| **26093** | Real-time stress and trauma assessment for the 14566 atrocities helpline (MoSJE) | Voice emotion analytics | Needs emotion models Gnani doesn't offer; sensitive victim data; not suitable |
| **26104** | Detection of voice-cloning impersonation (AICTE) | Anti-spoofing on live calls | Not a speech-recognition problem; Gnani's models don't do it; scam-call entries already exist |
| 26088 | Multilingual cooperative governance and legal chatbot (Ministry of Cooperation) | Multilingual, speech mentioned | Document Q&A, not a voice-first problem |
| 26042 | Vernacular pedagogy and real-time translation for mother-tongue primary education (Jharkhand) | Voice and translation | Translation isn't a Gnani model |
| 26173 | iTantra: Indian multilingual TTS and STT for low-bitrate radio links (ISRO) | STT and TTS used to carry voice as text over weak links | **Seen by title only.** Interesting for a "Jugaad" angle; hardware and radio make it risky |
| 26179 / 26172 / 26052 | Voice activator for edge devices; noise cancellation (ISRO, DRDO) | Hardware | Not applicable |

**Earlier SIH precedent:** SIH 2025 had an AI farmer query-support statement (PS 25076, seen in a mirror) and a Kerala statement asking for a Malayalam conversational farmer-advice interface (PS 25074, snippet only). Voice for farmers is a recurring SIH theme, so it's also a crowded one.

## 2. Problems from outside SIH
| Source | Problem | Takeaway |
|---|---|---|
| **IndiaAI Application Development challenge** | Indicative use cases: a voice or text agent giving government-scheme information in all Indian languages; grievance redressal and legal help through agents that use Bhashini | Same theme as SIH: scheme information by voice |
| **Bhashini challenges** | Live multilingual speech translation; voice-to-text medical transcription; real-time multilingual public-service assistance; VYOMA 2026 for open-source, voice-first AI that works offline | Government wants voice-first services in Indian languages |
| **RBI / NPCI** | Conversational payments on UPI by voice, in-app and on-call; UPI 123Pay already serves feature phones through IVR | Voice finance for feature-phone users is an active policy area |
| **Gnani's own examples** | Kannada farmer helpline; Hinglish kirana orders; noisy-call summariser; Tamil tutor | See [idea_research.md](idea_research.md) |
| **Gnani's own docs** | Real-time compliance monitoring of contact-centre calls; call analytics with diarization | What Gnani sells: calls at banks and contact centres |

## 3. How real are the problems?
| Claim | Evidence | Strength |
|---|---|---|
| Hundreds of millions of Indians reach services only by voice call | About **263.5 million 2G subscribers** at 31 March 2026 (Analysys Mason, cited by JPL); keypad-phone users estimated at 250–300 million. Over a quarter of households have no internet despite 95% mobile ownership; **35.6% of working-age women use the internet versus 57.6% of men** (secondary reports) | Moderate. Estimates differ by source and definition |
| Credit is how kiranas run | A 2022 Flourish Ventures and Bain study of 200 kiranas and 198 customers: about **a third of customers regularly use store credit**. Another study found every shopkeeper surveyed in Mumbai, Thane and Palghar kept extending credit after demonetisation. IIM Bangalore: credit retains customers | Moderate. Small samples; **no national share of kiranas offering udhaar was found** |
| Phone-based fraud is huge | The 1930 helpline reportedly took **32.4 million calls in 2025** (Moneylife). Parliament figures cited by Odisha Bytes: **1,23,672 digital-arrest cases and ₹1,935.51 crore lost in 2024**. Total-loss estimates vary widely (₹20,000 crore to ₹1.2 lakh crore) | Moderate. Official release not located |
| Frontline health workers drown in registers | mSakhi operations-research studies (86 ASHAs in Bahraich) and the Maatr app (about 90 workers in Karnataka, self-reported) | Weak. No rigorous time-saving measurement found |
| Farmer helplines are overloaded | No 2025 Kisan Call Centre figures found; only old totals | None for now |

## 4. What decides the choice
Criteria, drawn from [external_research.md](external_research.md) and [idea_research.md](idea_research.md):
1. **Gnani fit:** a live voice conversation, Indian languages, code-mixing, noisy phone audio, a real user problem.
2. **Uses our edge:** a real phone line, Telugu, Prisma v3.0.
3. **Measurable:** ground truth we can score end to end (the competing entries only test text parsers).
4. **Not crowded:** kirana, farmer helplines and scam detectors already have public entries.
5. **Doable alone:** 12 days to submit, 8 days to a postable demo (posts by Nov 5).
6. **Synthetic data only**, and safe: no medical or legal advice the agent could get dangerously wrong.

## 5. Candidates scored
Ratings are my judgement from the research above, not measurements.

| # | Candidate | Source | Gnani fit | Our edge | Measurable | Uncrowded | Effort (lower is better) | Risk |
|---|---|---|---|---|---|---|---|---|
| **A** | **Dukaan Dost + udhaar:** kirana orders and credit book on a phone line | Gnani example, kirana credit research | High | High | Medium (items and quantities) | Medium | Medium (stock list, order state, ledger) | Low |
| **D** | **Udyami Sahayak:** a phone line where a first-time rural entrepreneur says how much money they have and what business they want, and hears the project cost, the loan, the scheme, the rate and the instalment, spoken in their language | **SIH 26091** (with 26097 and IndiaAI scheme-information themes) | **High.** It's lending: what Gnani's customers (Equitas SFB, Bank of Baroda) do | High | **High.** The numbers are deterministic, so every call has an exact right answer | **High** (no public entry found) | **Low–medium.** Three slots (capital, business, place) plus a calculator, no catalogue | Medium: must be labelled indicative, because the scheme rules come from a problem statement |
| **B** | Telugu or Hindi **weather and crop advisory line** | SIH 26068, Gnani example 1 | High | Medium | Medium | **Low** (KisanSetu exists) | Medium (needs a live weather source) | Low |
| **E** | **Livestock disease reporting by IVR:** a farmer calls, describes the animal's symptoms, a rule-based triage flags suspected outbreaks, a vet dashboard clusters reports by village | SIH 26128 | Medium–high | High | Medium | High | Medium–high (triage rules, dashboard) | Medium: must never claim to treat animals |
| **C** | **Livelihood interview** by phone that recommends NSQF trades | SIH 26097 | High | High (IVR) | Low (no ground truth for "good advice") | Medium | Medium (NSQF data, recommender) | Medium |
| F | Patient history-taking by voice | SIH 26047 | Medium | Low | Medium | Medium | High (OCR, ABDM) | High (medical) |
| G | Scam-call shield | SIH 26104 and public entries | Low | Low | Medium | **Low** (two public entries) | Medium | Medium |
| H | Dictation like Wispr Flow | n/a | Low | Low | Medium | Medium | Low | Medium |

## 6. Findings
1. **Voice-by-phone for people on feature phones is the official theme.** SIH 2026 PS 26097 literally asks for IVR calls for feature-phone users, and the IndiaAI and Bhashini challenges ask for the same thing. Our real phone line fits that better than any browser demo.
2. **Candidate D scores highest on the criteria that decide the entry.** It's the only option where every call has an exactly checkable answer (slot filling plus arithmetic), which gives a much cleaner results table than item-and-quantity matching. It turns number understanding, the hard part of Hinglish and Telugu speech, into the thing we measure. It maps onto Gnani's lending customers and has no visible public entry.
3. **A is safer, because everything is already planned,** but kirana ordering is Gnani's own example, and a competing entry exists.
4. **B and G are the most crowded.** **F and E carry the most domain risk.**
5. **A mix is possible without diluting the entry.** The strongest "mixed" idea I found is **D with a kirana persona**: the caller is a would-be shopkeeper (the PS names Retail, Dairy and Textiles as example businesses), and the agent also knows the udhaar book as one of its topics. But two products in 12 days risks doing both shallowly, so I'd pick one as the core.

## 7. Recommendation
- **Build D (Udyami Sahayak) if you're willing to re-plan.** Most of the pipeline, the Gnani integration, the research and the versioning carry over unchanged. What changes is the domain files (a prompt, a scheme table and a calculator instead of a 60-item catalogue and an order state), which is *less* work than Dukaan Dost, and the evaluation, which becomes simpler and stronger. The PRD, the knowledge files and tasks 7–8 need rewriting.
- **Keep A if you'd rather not re-plan.** It's lower risk, and the credit book already differentiates it.
- Either way, **write nothing in the README that the evaluation hasn't measured**, and label scheme figures as *indicative* until checked against the actual scheme documents.

## Sources
- SIH 2026 catalogue mirrors: https://sih-2026-problem-statements.shaikrohit187.workers.dev/public/pdfs/SIH_2026_All_PS.pdf, https://www.blinknbuild.in/Assets/SIH_2026_All_226_Problem_Statements_Master_Catalogue.pdf (unofficial; official portal is sih.gov.in)
- SIH 2025 mirror: https://www.driems.ac.in/wp-content/uploads/2025/09/Smart-India-Hackathon_PROBLEM-STATEMENTS.pdf
- Bhashini challenges: https://innovateindia.mygov.in/bhashini-challenge/, https://bhashini.gov.in/hackathon
- IndiaAI Innovation Challenge: https://d12aarmt01l54a.cloudfront.net/cms/files/innovation-challenge-2026-1/1768810163.pdf
- Conversational payments on UPI: https://www.fintechfutures.com/ai-in-fintech/ai-powered-conversational-payments-to-launch-on-india-s-upi
- Feature-phone base: https://www.weforum.org/stories/geographies-in-depth/mobile-phone-digital-divide-inclusion/ and the Analysys Mason figure cited in https://tele.net.in/?p=50432
- Kirana credit: https://theprint.in/ani-press-releases/retails-digitization-boom-is-not-leaving-kirana-stores-behind/1145138, https://repository.iimb.ac.in/handle/2074/18361, https://scroll.in/article/826855/scroll_in
- Fraud: https://moneylife.in/article/fraud-alert-india-is-losing-over-22000-crore-a-year-in-cyber-scams-and-the-worst-is-yet-to-come/80612.html, https://odishabytes.com/digital-arrest-scam-govt-blocks-83000-whatsapp-accounts-7-8-lakh-sim-cards-know-how-to-stay-safe
- ASHA tools: https://www.intrahealth.org/sites/default/files/attachment-files/msakhibrieffinal.pdf, https://www.capgemini.com/news/inside-stories/tracking-maternal-health/
- Competing Gnani entries: see [idea_research.md](idea_research.md)
