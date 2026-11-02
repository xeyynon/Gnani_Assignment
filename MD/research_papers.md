# Research papers

Published work that bears on Dukaan Dost, grouped by the problem it addresses. Each entry says what the paper shows and how it supports (or limits) our approach.

**Found: 2026-10-28, by web search. Read in full text: 2026-10-28** for the papers marked "Yes" in the table in Part 2. The rest are still known from search summaries only. Before you quote a number in the README, a video or the submission, check it against the paper (rule R-5): several papers contradict their own abstracts (noted below). Vendor blogs are listed separately and marked; they are not research.

**Part 1** lists the papers by problem. **Part 2** (at the end) records what the full texts say, corrects Part 1 where it was wrong, and picks the methods we will use.

---

## 1. Problem: callers mix Hindi and English (Hinglish), and Indian-language speech recognition is hard

**Why it matters.** Our callers will say "do kilo atta aur one litre oil dena" in one sentence. Recognisers trained on one language at a time handle that badly.

| Paper | What it shows | Supports our approach |
|---|---|---|
| Sreeram, Dhawan, Sinha. *Hindi-English Code-Switching Speech Corpus* ([arXiv 1810.00662](https://arxiv.org/pdf/1810.00662)) | Built a Hinglish speech corpus because none large enough existed | The problem is real and was under-served; we should test on code-mixed speech, not only clean Hindi |
| Srivastava et al. *End-to-End ASR for Code-switched Hindi-English Speech* ([arXiv 1906.09426](https://arxiv.org/pdf/1906.09426)) | End-to-end models trained on under 50 hours of data | Code-mixed data is scarce, so a model trained for it (Prisma's `codemix`) is a sensible choice |
| *Investigating Target Set Reduction for End-to-End Speech Recognition of Hindi-English Code-Switching Data* ([arXiv 1907.08293](https://arxiv.org/pdf/1907.08293)) | Proposes a scheme to improve code-switching recognition | Background on why mixed-language output is hard |
| Hussein et al. *Balanced End-to-End Monolingual pre-training for Low-Resourced Indic Languages Code-Switching Speech Recognition* ([arXiv 2106.05885](https://arxiv.org/abs/2106.05885v2)) | Reports a 14.1% relative WER gain on Hindi-English (MUCS 2021, third place) | Shows the size of improvement a code-switch-aware model can give |
| Chadha et al. *Code Switched and Code Mixed Speech Recognition for Indic languages* ([arXiv 2203.16578](https://arxiv.org/abs/2203.16578v2)) | Reports WER of 21.77 (Hindi-English) and 28.27 (Bengali-English) | A reference range: code-mixed WER is high, so we must measure ours rather than assume |
| Ganji et al. Interspeech 2018, language modelling for Hindi-English intra-sentential switching ([PDF](https://www.isca-archive.org/interspeech_2018/ganji18_interspeech.pdf)) | Language modelling for switches inside one sentence | Background |

**Benchmarks and datasets for Indian speech (useful for our evaluation chapter)**

| Paper | What it shows |
|---|---|
| Javed et al. *IndicVoices: Towards building an Inclusive Multilingual Speech Dataset for Indian Languages* ([arXiv 2403.01926](https://arxiv.org/html/2403.01926v1)) | About 7,348 hours from 16,237 speakers over 22 languages, with read, extempore and conversational speech; includes an ASR benchmark |
| Bhogale et al. *Vistaar: Diverse Benchmarks and Training Sets for Indian Language ASR* ([arXiv 2305.15386](https://arxiv.org/pdf/2305.15386), Interspeech 2023) | 59 benchmarks over 12 languages. Commercial recognisers were weaker than the open IndicWhisper on most; on Hindi the paper reports 13.6 WER for IndicWhisper against 23.9 (Google) and 20.0 (Azure) |
| *IndicVoices-R* ([NeurIPS 2024](https://neurips.cc/virtual/2024/poster/97858)) | A multi-speaker corpus for Indian text-to-speech: 1,704 hours, 22 languages |

**What this means for us.** The papers back the decision to use a model built for Indian languages and code-mixing, and they give a way to report results: word error rate per language plus a code-mixed set. They also warn that general-purpose recognisers do worse on Indian speech, which is the case for trying Prisma against what we run today. They do not say Prisma is better. Only our own evaluation can say that.

---

## 2. Problem: a voice agent must answer fast, and handle interruptions

**Why it matters.** A shopkeeper's customer will hang up on a slow agent. Our pipeline chains speech recognition, a language model and speech synthesis, and each adds delay.

| Paper | What it shows | Supports our approach |
|---|---|---|
| *DDTSR: Discourse-Aware Dual-Track Streaming Response* ([arXiv 2602.23266](https://arxiv.org/html/2602.23266v1)) | A strictly sequential recogniser-model-synthesiser pipeline has high response delay; overlapping the stages reduces it. Natural turn-taking needs a response within a few hundred milliseconds | Our streaming design (stream the reply to TTS while Gemini is still writing) is the recommended direction |
| *LTS-VoiceAgent* ([arXiv 2601.19952](https://arxiv.org/html/2601.19952v1)) | Frames the trade-off: end-to-end speech models lack deep reasoning, cascaded pipelines are slow | Explains why we keep a cascade (we need reasoning plus exact prices) and work on its speed |
| *Enterprise Realtime Voice Agents* tutorial ([arXiv 2603.05413](https://arxiv.org/pdf/2603.05413v1)) | An open cascaded build (streaming recogniser, model with function calling, streaming synthesiser). **Corrected after reading:** 947 ms is an *estimate* (the three stage times added up, a "sequential upper bound"); the only end-to-end measurement is 755 ms. It reports no accuracy and no barge-in speed | A reference point for **time to first audio**, to be compared with care: ours must be measured end to end |
| *ChipChat: Low-Latency Cascaded* ([arXiv 2509.00078](https://arxiv.org/html/2509.00078v1), Apple) | A streaming cascade where the recogniser doubles as the voice-activity detector and signals interruptions downstream | Same shape as our barge-in design |
| *DuplexCascade* ([arXiv 2603.09180](https://arxiv.org/abs/2603.09180)) | Notes that most cascades use an outside VAD to decide turn boundaries, and proposes partial-transcript micro-turns with control tokens | A possible later improvement; ours is the simpler, VAD-based design |

**Turn detection (when has the caller finished?)**

| Paper | What it shows |
|---|---|
| *Speculative End-Turn Detector for Efficient Speech Chatbot Assistant* ([arXiv 2503.23439](https://arxiv.org/pdf/2503.23439)) | Telling a finished turn from a pause mid-sentence is a separate problem from voice detection; releases a dataset and a small model |
| *Streaming Endpointer for Spoken Dialogue using Neural Audio Codecs and Label-Delayed Training* ([arXiv 2506.07081](https://arxiv.org/html/2506.07081v2)) | Fixed-delay silence rules add needless latency; learned endpointers trade latency against errors. After reading: its baseline is a learned Mel endpointer, not a fixed-silence VAD, and its abstract and tables disagree on some numbers |
| *Optimizing Endpointing Thresholds using Dialogue Features* (SIGdial 2008, [PDF](https://preview.aclanthology.org/fix_video/W08-0101.pdf)) | Argues fixed silence thresholds are too simple and proposes adaptive ones |
| *Thai Semantic End-of-Turn Detection for Real-Time Voice Agents* ([arXiv 2510.04016](https://arxiv.org/pdf/2510.04016)) | A non-English example of the same problem |

**What this means for us.** The literature supports a streaming cascade with a voice detector for turn ends, which is what we have. It also names our weak spot: a fixed silence threshold cuts people off mid-sentence, especially someone listing items slowly ("atta... do kilo... aur dal"). Prisma's own VAD settings and the `commit` frame are worth testing for this. We should measure time to first audio and report it next to the 947 ms reference, as our own number from our own run.

---

## 3. Problem: language models get arithmetic and money wrong

**Why it matters.** An order total or a loan EMI that is off by a rupee loses trust, and a made-up price is worse. Our rule is that code computes money and the model only speaks it.

| Paper | What it shows | Supports our approach |
|---|---|---|
| Gao et al. *PAL: Program-aided Language Models* ([ICML 2023](https://proceedings.mlr.press/v202/gao23f.html), [arXiv 2211.10435](https://arxiv.org/abs/2211.10435v1)) | Models often decompose a problem correctly but err in the arithmetic; letting a Python interpreter do the solving beat chain-of-thought by an absolute 15% on GSM8K and by about 40% on a harder variant | Direct support for computing totals and EMI in code |
| Schick et al. *Toolformer: Language Models Can Teach Themselves to Use Tools* ([arXiv 2302.04761](https://ar5iv.labs.arxiv.org/html/2302.04761)) | LLMs struggle with basic arithmetic that simple tools do exactly; the model can learn when to call a tool | Same principle: send exact work to a tool |
| Fatahi Bayat, Pezeshkpour, Hruschka. *From Proof to Program: Characterizing Tool-Induced Reasoning Hallucinations in Large Language Models* ([arXiv 2511.10899](https://arxiv.org/abs/2511.10899)) | Even with correct tool use, models can treat tool output as a substitute for reasoning; errors move from arithmetic to logic and assumptions | A limit: a tool fixes the sums, not the model's wrong interpretation (e.g. the wrong item chosen) |

**What this means for us.** The papers justify our design, and the third one tells us where it can still fail: the model may pick the wrong item or quantity and the code will then calculate that mistake exactly. That is why the evaluation measures **order accuracy** (right items and quantities), and not only whether the total adds up.

---

## 4. Problem: ordering by voice, in practice

| Source | What it shows |
|---|---|
| Zeng, Gupta. *AutoManager* ([arXiv 2505.06438](https://arxiv.org/abs/2505.06438v1)) | A dual-agent LLM system for a drive-thru, combined with Answer Set Programming (rules the model cannot break). **Corrected after reading:** text input only; the evidence is a human rating of five conversation pairs by five graders, against Taco Bell transcripts taken from online videos. Treat "more reliable" as a small, informal result |
| *Conversational food ordering agent field study* ([CEUR-WS Vol-4101, paper 8](https://ceur-ws.org/Vol-4101/paper8.pdf), Google Cloud) | A pilot at two restaurant chains; most guests reacted positively to the agent |
| Qin, Zhou. *Eva* ([AAMAS 2025 demo](https://aamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p3035.pdf)) | A multilingual voice agent network for restaurant phone orders; it leaves evaluation out |

**What this means for us.** Voice order-taking is an established use. Two lessons carry over: keep hard rules outside the model (AutoManager's idea, which matches our stock list and code-computed totals), and evaluate properly, because the demo-paper (Eva) skips it. Our 20 scripted orders with an order-accuracy score fill that gap. I found no paper on voice ordering for kirana shops, or in Indian languages, specifically.

---

## 5. Problem: the phone line is narrow and noisy

| Paper | What it shows |
|---|---|
| Lin et al. Interspeech 2023, noise-robust bandwidth expansion for call-centre speech ([PDF](https://www.isca-archive.org/interspeech_2023/lin23f_interspeech.pdf)) | Narrowband (8 kHz) noisy phone speech hurts recognition; a bandwidth-expansion model cut WER by 11.71% on a real IVR system. **Corrected after reading:** the audio is English and Mandarin call-centre speech, not Indic, and better audio-quality scores (PESQ, STOI) did not always mean better WER |
| *Factors affecting ASR performance: A study using state of the art ASR models in Indic Languages* ([arXiv 2606.09335](https://arxiv.org/pdf/2606.09335), preprint) | **Corrected after reading:** zero-shot tests of open Indic models on Hindi (audio experiments) and four other languages (speaker factors). The text gives **no numeric WER**, only trends: the GSM (2G) codec hurt consistently; narrowband and wideband codecs stayed close to clean 16 kHz audio; Opus barely hurt; classical resampling cost a moderate amount; neural restoration (VoiceFixer, AudioSR) made WER *worse*; below 8-bit depth recognition degraded sharply. Whisper-based models coped with competing speech better than Conformer ones |
| EUSIPCO 2014, wideband telephone ASR ([PDF](https://new.eurasip.org/Proceedings/Eusipco/Eusipco2014/HTML/papers/1569910419.pdf)) | Cites a 20% relative WER reduction from doubling the sampling rate from 8 to 16 kHz |

**What this means for us.** If callers come in over a real phone number, the audio is 8 kHz and will be worse than the 16 kHz browser audio we test with today. The Indic preprint suggests plain resampling is the safe way to get to 16 kHz. Our noisy test set (mixing in shop, traffic or fan noise at about 10 dB) is how we show the effect on our own system. The second paper is a preprint and I did not open it.

---

## 6. Problem: shop credit (udhaar) is informal and unrecorded, and small borrowers lack guidance

| Source | What it shows |
|---|---|
| Sungu, Alhorr, Srivastava. *Between Trust and Trade: on Informal Credit Networks in India* ([London Business School blog](https://wheelerblog.london.edu/between-trust-and-trade-on-informal-credit-networks-in-india-2/)) | Household survey data show more people borrow from shops than from banks, self-help groups, friends, relatives or moneylenders. In a survey of about 200 store owners, only about half kept any written records |
| IFMR LEAD, *Digital lending for small merchants: the missing road to the last mile* ([note](https://ifmrlead.org/digital-lending-for-small-merchants-the-missing-road-to-the-last-mile)) | Discusses digital footprints as a route to formal credit for small merchants |

I could not confirm whether the Sungu paper is formally published, so check its status before citing it as a journal article.

**Voice interfaces for people with low literacy**

| Paper | What it shows |
|---|---|
| Patel et al. *Avaaj Otalo*, CHI 2009 ([PDF](https://hci.stanford.edu/publications/2009/chi2009_patel.pdf)) | With 45 farmers in rural Gujarat, speech and keypad input had no clear preference; in a pilot most first-month calls used touchtone |
| *FarmChat* ([PDF](https://ubicomplab.cs.washington.edu/pdfs/farmchat.pdf), University of Washington) | A conversational agent for farmers near Ranchi, tested with 34 people; preferences for audio-only versus audio and text varied by user |
| 2025 study on conversational access to welfare schemes (15 low-income participants, found via search; I did not note the exact title) | Conversational design fits the mental models of new smartphone users better than a form-based app |
| Microsoft Research, text-free user interfaces | Design principles from work with 570 low-literate participants in India, the Philippines and South Africa |

**What this means for us.** The credit-book idea rests on a real gap (half of shopkeepers keep no written record). The HCI studies show that voice is a workable way in for people who do not read well, but the farmer studies caution that some users prefer keypad input, so a voice-only system should have a clear fallback. I found no peer-reviewed paper on a voice agent that gives loan guidance in Indian languages. That is also a gap our entry could fill, but it means we have no published baseline to compare against.

---

## 7. Problem: serving many callers at once

I found **no peer-reviewed paper** on serving concurrent voice-agent calls. What exists:

| Source | What it says | Kind |
|---|---|---|
| The tutorial in section 2 ([arXiv 2603.05413](https://www.emergentmind.com/papers/2603.05413)) | Measures one session only. It does not address scaling beyond one session | Paper, with an explicit limit |
| Amazon Nova Sonic design post ([AWS blog](https://aws.amazon.com/blogs/machine-learning/scalable-voice-agent-design-with-amazon-nova-sonic-multi-agent-tools-and-session-segmentation/)) | Isolates each session to avoid noisy-neighbour slowdowns | Vendor blog |
| Practitioner guide ([edesy.in](https://edesy.in/docs/voice-agent/advanced/scaling), [dograh.com](https://www.dograh.com/feeds/blog/scale-concurrent-calls)) | Peak concurrency, not daily call volume, sets capacity; STT, LLM and TTS service limits usually cap you before your own server does | Practitioner blogs |

**What this means for us.** Per-call session isolation (our plan) is the common industry pattern, but we cannot cite a paper for it. The practical point matches our worry: our Gnani and Gemini account limits (B-07) will set the call cap before our own machine does. A small shop will probably see few simultaneous calls, so the cap can start low.

---

## Vendor material (not research)

These came up in the search. They are marketing or product pages, so do not quote their numbers.
- Gnani.ai blog posts on voice bots in financial services ([1](https://www.gnani.ai/?p=44921), [2](https://www.gnani.ai/resources/blogs/the-rise-of-multilingual-banking-serving-indias-next-billion)) make claims such as a 65% cut in loan processing time, with no source named. Gnani's page on telephone acoustic models (14 million hours) is [here](https://gnani.ai/resources/research/how-we-train-acoustic-models-on-14-million-hours-of-telephonic-speech); I did not verify the study it cites.
- Deepgram's Hinglish article, caller.digital's 8 kHz benchmark and OkCredit's 2021 report ($400-500 billion of retail trade on credit is its estimate).
- The LTF "KAI" assistant ([page](https://lab.ltfinance.com/kai-ltf-labs-workhorse-for-inclusive-ai-in-financial-services/)) is a related product for loan eligibility questions and form filling in underserved areas.

---

## Summary: what the research supports, and what it does not

| Our decision | Backed by | Evidence strength |
|---|---|---|
| Use an Indian-language, code-mix-aware recogniser | Section 1 | Strong that the problem exists; none show Prisma specifically |
| Streaming cascade with a voice detector | Section 2 | Good (several papers) |
| Code computes money, the model speaks it | Section 3 | Strong (PAL, Toolformer), with a stated limit |
| Rules and a stock list outside the model | Section 4 (AutoManager) | One paper |
| Measure order accuracy and noisy audio | Sections 3 to 5 | Reasoned from the papers' gaps |
| Credit book for shops | Section 6 | Good on the gap, weak on voice systems |
| One session per call | Section 7 | Industry practice only |

**Gaps in the literature.** I found no paper on (a) voice agents for kirana shops, (b) voice loan guidance in Indian languages, or (c) serving concurrent voice-agent calls. These are places where our entry has no published baseline, and the README must not imply otherwise.

**To do before using any figure:** open each paper and confirm the number, the venue and the year. Several arXiv IDs here come from search results alone, and I could not check them against the full text.

---

# Part 2: what the full texts say, and the methods we take

## How much I read

"Read" means I got the paper's full body text (through a fetch tool that summarises, plus `pdftotext` where the PDF would not summarise). It does not mean I checked every table by hand.

| Paper | Read | Notes |
|---|---|---|
| Enterprise Realtime Voice Agents ([2603.05413](https://arxiv.org/html/2603.05413v1)) | Yes (HTML) | 947 ms is an estimate; 755 ms is the measured end-to-end figure; the paper's wording is inconsistent |
| DDTSR ([2602.23266](https://arxiv.org/html/2602.23266v1)) | Yes | English only; the reported 17.5% does not match its own table (about 20%) |
| ChipChat ([2509.00078](https://arxiv.org/html/2509.00078v1)) | Yes | Needs a 192 GB Mac; no accuracy evaluation in the text |
| Speculative End-Turn Detector ([2503.23439](https://arxiv.org/html/2503.23439v1)) | Yes | Real-data F1 is low for every model (best 53.1) |
| Streaming Endpointer ([2506.07081](https://arxiv.org/html/2506.07081v2)) | Yes | Abstract and tables disagree (35% vs about 55%; 1640 vs 1690 ms) |
| Indic ASR factors ([2606.09335](https://arxiv.org/html/2606.09335v1)) | Yes | No numeric WER given; SNR levels not stated |
| AutoManager ([2505.06438](https://arxiv.org/html/2505.06438v2)) | Yes | Text only; five conversation pairs rated |
| Code Switched and Code Mixed ASR ([2203.16578](https://arxiv.org/pdf/2203.16578)) | Yes (`pdftotext`) | Table text partly garbled; abstract numbers used |
| Noise-Robust Bandwidth Expansion ([Lin et al.](https://www.isca-archive.org/interspeech_2023/lin23f_interspeech.pdf)) | Yes (`pdftotext`) | English and Mandarin |
| From Proof to Program ([2511.10899](https://arxiv.org/abs/2511.10899)) | Abstract page only | Math benchmark, not ordering |
| PAL ([2211.10435](https://arxiv.org/abs/2211.10435)) | Abstract page only | Well known; the claims match its abstract |
| Vistaar ([2305.15386](https://arxiv.org/pdf/2305.15386)) | Yes (`pdftotext`) | Hindi telephone speech (Gramvaani) is far harder than clean speech; see pipeline_expectations.md |
| IndicVoices ([2403.01926](https://arxiv.org/html/2403.01926v1)) | Partly (first 100,000 of 149,327 characters) | Hindi and Telugu WER by system |
| The Hinglish corpus papers, DuplexCascade, LTS-VoiceAgent, Toolformer, the HCI studies and the credit-network study | **No** | Search summaries only |

## What each paper gives us (methods, not just claims)

**Enterprise Realtime Voice Agents (the cascade recipe).**
- Audio goes to the recogniser in 20 ms chunks; only final transcripts go to the model.
- A state machine drives the call: IDLE, LISTENING, PROCESSING, SPEAKING, INTERRUPTED. Processing starts after 700 ms of silence.
- Model tokens fill a sentence buffer. A sentence is released at `.`, `!` or `?` followed by a space, **except abbreviations and decimal numbers**, and sentences under 10 characters are held back. Speech synthesis starts on the first complete sentence while the model keeps writing.
- Echo is handled twice: browser echo cancellation plus a server gate that attenuates the microphone while the agent speaks.
- Stage times at the median (cloud model): recogniser 402 ms, model first token 457 ms, synthesis first byte 221 ms.

**ChipChat (barge-in done properly).**
- When the recogniser hears speech while the agent is talking, it tells every downstream part to stop.
- The player reports *which words were actually spoken* when it was cut off. The model then drops text that was generated but never spoken from its memory, so it does not act as if the caller heard it.
- A single "pause length" setting trades latency against false interruptions by short noises; the paper does not measure that trade-off.

**DDTSR (cutting the wait the caller feels).**
- A tiny model emits a short filler word ("well", "so") while the caller is still finishing, gated by a confidence score. The large model's answer plays when the filler ends.
- Reported saving: 19% to 51% of waiting time, with no loss of answer quality on two English benchmarks.
- Fillers carry no facts, so they cannot contradict the later answer. Caution: it is tested on English only, and the gain depended on how often a filler fits (94% of one dataset's turns, 38% of the other's).

**Speculative End-Turn Detector and Streaming Endpointer (when has the caller finished?).**
- A fixed silence threshold cannot tell the end of a turn from a pause. A small always-on model plus a large model that is called only when silence appears cut compute roughly 38 times (the paper says "more than 10 times"), but accuracy on real speech stays low.
- The endpointer paper shows the real problem: it is a trade between **cutting people off** and **waiting too long**, and it reports both (cutoff error at a fixed median latency). Neither paper is trained on Indian languages or on item-listing speech.
- Both need trained models, so we will not build them. We take the idea of reporting cutoff rate and latency together.

**AutoManager (keeping the model inside the menu).**
- The model's only job is to turn the caller's words into a fixed set of facts (`order(item)`, `update(item, change)`). A rule engine then decides whether the order is allowed.
- New facts are checked against the existing order first and only then accepted. A dish that is out of stock is rejected by rule, never by the model.
- Misspelled item names are matched to the menu by embedding similarity.
- Limits: text input only, and very little evaluation.

**Code Switched and Code Mixed ASR (Hindi-English).**
- Training one model per language pair beat one shared model.
- For multilingual input, a language-identification step before language-specific models improved results by about 51% on the paper's setup.
- English words appear in Latin script or in Devanagari in the transcripts, so plain WER punishes correct output. The authors add **transliterated WER (T-WER)**, which counts an English word as correct in either script. Their Hindi-English result is a WER of 21.77.

**Indic ASR factors and bandwidth expansion (phone audio).**
- Wideband (8 kHz-bandwidth) phone audio stays near clean 16 kHz quality. Old GSM coding is the damaging case.
- Use classical resampling to reach 16 kHz. Neural "restoration" sounds better and recognises worse.
- Better audio-quality scores do not mean better recognition, so judge a front-end by WER only.

**PAL and the tool-myopia paper (money).**
- PAL: the model writes the steps, a program does the arithmetic, and that beat the model reasoning alone on arithmetic problems.
- The newer paper warns that tool use moves mistakes from arithmetic to wrong interpretation, and that answers can be right without sound reasoning. Its mitigation is a training method we cannot use.

## Conclusions

1. **The architecture is right.** A streaming cascade with a voice detector, a rule layer for money and stock, and a language model for understanding is what the papers describe. No paper shows a better way for our constraints (a hosted STT/TTS API, no GPU, a solo build).
2. **The risks are in understanding, not arithmetic.** PAL and the myopia paper agree that code fixes the sums but not the choice of item. So order accuracy, not total accuracy, is the number that matters.
3. **Our evaluation can be more careful than the literature.** The ordering papers rate five conversations by hand or skip evaluation. Twenty scripted orders scored automatically, clean and noisy, is a stronger result than any of them reports, as long as we report only what we measure.
4. **Several strong-looking numbers are unreliable.** The papers' own abstracts and tables disagree in four places. We quote none of these figures in our own materials.
5. **Gaps stay open.** Nothing published covers kirana ordering, Indian-language voice loan guidance, or concurrent call serving. Say so in the README and do not imply a baseline.

## Methods we will use

| # | Method | From | How it applies | What we measure |
|---|---|---|---|---|
| M1 | **Sentence-buffer streaming to TTS**, skipping abbreviations and decimals, holding sentences under 10 characters | Enterprise tutorial | Our replies are full of prices and weights ("1.5 kg", "Rs 45.50"); a splitter that breaks at the decimal point would read them wrongly | Time to first audio; a test that "1.5 kg" is never split |
| M2 | **Barge-in that records what was actually spoken** and removes the unspoken rest from the model's history | ChipChat | Stops the agent saying "I added atta" about text the caller never heard | A scripted interruption: history after the cut equals the spoken part |
| M3 | **Echo gate** (browser echo cancellation plus a server-side gate while the agent speaks) | Enterprise tutorial | Already planned; matters most on phone speaker audio | False interruptions per call |
| M4 | **Rule layer between the model and the order**: the model extracts item and quantity into a fixed form; code checks it against the stock list and the current order and does all sums | AutoManager, PAL | Out-of-stock and unknown items are rejected by code, never invented | Order accuracy: right items and quantities; count of invented items |
| M5 | **Fuzzy item-name matching** to the stock list, plus Prisma key terms (`x-keyterms`) for product names | AutoManager | Fixes "maggi", "magi", "मैगी" | Per-item match rate on the noisy set |
| M6 | **Language hints, not a hard lock**: give Prisma the list of likely languages; keep our per-call lock after the caller's first sentences | Chadha et al. (idea only) | The paper's identify-then-recognise result supports narrowing the language; we use the vendor's hint list rather than build it | WER per language on Hindi, Telugu, English, Hinglish |
| M7 | **T-WER**: score English words as correct in Latin or Devanagari/Telugu script | Chadha et al. | Without it, Hinglish WER is inflated by script, not by errors | Both WER and T-WER in the results table |
| M8 | **Plain resampling** (8 to 16 kHz) for phone audio; no neural enhancement | Indic ASR factors | When the phone number arrives; keep wideband codecs if the provider allows | WER on 8 kHz and 16 kHz copies of the same script |
| M9 | **Cutoff rate and latency reported together** | Endpointer papers | Tune Prisma's VAD settings and the `commit` frame on item-listing speech, and report both numbers | Cutoff rate (caller interrupted mid-list) at a fixed time to first audio |
| M10 | **Call-state machine** (IDLE, LISTENING, PROCESSING, SPEAKING, INTERRUPTED) | Enterprise tutorial | Matches what `app.py` already does; makes per-call sessions easier to build | Covered by the session tests |
| M11 | **Short acknowledgement while the model thinks** (optional) | DDTSR | A canned "ji, ek minute" in the caller's language could hide a slow first token. Only worth it if M1 leaves time to first audio too high | Time to first audio with and without; do callers hear a contradiction |

**Not taken:** training our own end-of-turn model (no data, no time), full-duplex speech-to-speech models (no function calling, too slow per the tutorial), neural audio restoration (hurts recognition).

## Still to read before Nov 5

Vistaar and IndicVoices (to choose our WER protocol), the Hinglish corpus paper (to choose the code-mixed test set), PAL's full text (our prompt format), and the credit-network study (to check what the half-keep-no-records figure rests on).
