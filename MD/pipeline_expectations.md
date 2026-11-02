# Pipeline and expectations

What each stage of the pipeline can be expected to do, with the evidence behind it. Written before building the order flow and the Gnani backends, so that the evaluation can be checked against expectations set in advance.

**Evidence labels used throughout**

| Label | Meaning |
|---|---|
| **Published** | A peer-reviewed or arXiv result I read (see [research_papers.md](research_papers.md)) |
| **Vendor claim** | Said by Gnani or another vendor. Not independent. Never quoted as our result |
| **Docs** | Stated on docs.gnani.ai, read 2026-10-28 |
| **Unknown** | Nobody has told us and we have not measured |
| **Target** | A goal we set. It is not a prediction and not a result |

**Rule R-5 applies to this file.** Nothing here is a result of ours. Every figure from our own runs goes in `evaluation/results/`, and only those figures go in the README.

---

## 1. The pipeline we are expecting to run

```
caller audio (16 kHz in the browser; 8 kHz on a real phone line)
  → webrtcvad end-of-speech  (hangover 650 ms today, VAD_HANGOVER_MS)
  → Prisma v3.0 over WebSocket  (a transcript arrives per sentence, not per word)
  → Gemini (system prompt + stock list + history) streaming
  → sentence splitter → Timbre v3.0 (one request per connection) → audio out
  → code: stock check, totals, EMI, order file
```

---

## 2. Stage by stage

### 2.1 Speech recognition (Prisma v3.0)

**What the evidence says**

| Evidence | Figure | Label |
|---|---|---|
| Hindi, clean read speech (Kathbath), public systems | Google 14.3, Azure 13.6, best open model 10.3 WER | Published (Vistaar) |
| Hindi, **spontaneous telephone speech** (Gramvaani) | Google 59.9, Azure 42.3, best open model 26.8 WER | Published (Vistaar) |
| Hindi vs Telugu, conversational speech (IndicVoices benchmark) | Their own IndicASR model 15.0 (Hindi), 26.8 (Telugu); USM 20.5 / 40.3; Azure 27.2 / 53.3 | Published (IndicVoices) |
| Gnani on Hindi clean (Kathbath) / telephone (Gramvaani) | 8.38 / 26.24 WER | **Vendor claim** (Gnani's benchmarking article) |
| Gnani on Gramvaani, on another Gnani page | 3.8 WER | **Vendor claim, contradicts the line above** |
| Gnani on Hindi-English telephone speech | 9% WER | Vendor claim, from their own production audio |
| Prisma v3.0 accuracy numbers | None given | Docs |
| Prisma v3.0 noise and 8 kHz behaviour | Not stated | Docs |

**Reading it.** Telephone speech is far harder than clean speech: on Gramvaani every system scores between two and a half and four times worse than on clean Hindi. Telugu is harder than Hindi on every system. Gnani's two statements about Gramvaani differ by a factor of seven (3.8 vs 26.24), so neither can be used until we measure it ourselves.

**What Prisma v3.0 offers us (Docs)**
- 1 to 4 language hints, or automatic detection, with the detected language returned. This is a hint and not a lock.
- `x-format`: `verbatim`, `transcribe`, `codemix` or `transliterate`. Code-mixed output keeps English words readable.
- `x-keyterms`: up to 200 words or short phrases. Gnani tested it on "60 public clips per combination" and says it never made things worse, but also warns that context can reduce accuracy, so test with and without.
- Transcripts arrive **as each sentence completes**. There is no word-by-word streaming, so the speech recogniser's delay is part of the wait after the caller stops.
- Limits: sessions last at most 15 minutes; idle timeout 60 s by default; the number of simultaneous sessions is a per-organisation cap whose value is **not published** (it is shown at app.gnani.ai).
- No word timestamps. Hindi and Marathi can be confused on very short utterances.
- The `commit` frame **is** documented, on the realtime WebSocket page (all models), but the Prisma v3.0 model page does not mention it. `stt_gnani.py` sends it and also sends trailing silence as a fallback. Confirm with the real service.

**Expectations (hypotheses to test, not claims)**

| Condition | What I expect | Basis |
|---|---|---|
| Hindi, clean 16 kHz, synthetic speech from Timbre | Low WER, likely single digits to low teens | Published clean-speech results; but Timbre speech is easier than real people, so this will flatter us |
| Hindi-English mixed, clean | Higher than pure Hindi; worse if scored without T-WER | Published (code-switching papers) |
| Telugu, clean | Clearly worse than Hindi | Published |
| Any language, with 10 dB noise or 8 kHz | Large rise, possibly doubling | Published (Gramvaani gap); unknown for Prisma |
| Item names (Maggi, Amul butter) | Fewer errors with `x-keyterms` | Docs claim; test it |

**Biggest risk.** Synthetic callers (Timbre reading our scripts) are much easier than real callers. Our results will be optimistic. The README has to say the test speech is synthetic, and a handful of human recordings would show the gap.

---

### 2.2 Knowing when the caller has finished (endpointing)

- Today: a fixed `VAD_HANGOVER_MS` of 650 ms in `app.py`, plus Prisma's own settings (`x-min-silence-ms` and others).
- **Published:** a fixed silence wait cannot tell a pause from the end of a turn. The streaming-endpointer paper shows the real trade-off is cutting the caller off versus waiting too long, and reports both. The tutorial paper uses 700 ms.
- **Risk for us.** People list items slowly ("atta... do kilo... aur dal... teen packet"). A 650 ms wait may cut them off between items.
- **Expectation.** Some cutoffs will happen on item lists. We cannot predict the rate. We will count them.

---

### 2.3 The language model (Gemini)

| Evidence | Figure | Label |
|---|---|---|
| Gemini 2.5 Flash-Lite, median time to first token | 1,337 ms | Third-party tracker (OrcaRouter, August 2026); method unknown |
| Gemini 3.1 Flash-Lite on Artificial Analysis | About 5.8 to 6.2 s, with a 10,000-token input; the page value changed between captures | Third-party tracker; not our prompt size |
| Gemini 3.5 Flash-Lite | Page exists; I did not get its figure | Unknown |
| Our prompt (system prompt + 60-item stock list + history) | Not measured | Unknown |

**Reading it.** I found no trustworthy time-to-first-token for the model we plan to use. The two trackers disagree by a factor of four, probably because they use different input sizes and different dates. **This is the largest unknown in the latency budget**, and it is cheap to measure: one call with our real prompt.

**Other expectations**
- Zero-shot LLMs do worse on code-mixed text than on single-language text (Published, several Hindi-English studies). Gemini is mentioned as promising but behind specialised models on code-mixed named entities. Order extraction is a similar task, so expect errors on mixed-language item names and quantities.
- No published order-extraction accuracy exists for Hindi, Telugu or mixed speech. We have no baseline.

---

### 2.4 Speech synthesis (Timbre v3.0)

| Item | Value | Label |
|---|---|---|
| Latency | No figure published | Docs |
| Concurrency | No limit stated; docs advise "one synthesis request at a time" for lowest latency | Docs |
| Sample rates | 8000, 16000, 22050, 24000, 44100, 48000 Hz; `mulaw` and `alaw` containers are forced to 8 kHz | Docs |
| Speed | 0.85 to 1.15 | Docs |
| Voices | 13 voices, each speaking all 10 languages; audio tags supported | Docs |
| OGG output | Delivered as one chunk after synthesis, so not streamed | Docs |
| Old reference in `app.py` | A comment records about 0.25 to 0.35 s to the first chunk for Google TTS once warm | Our own old observation, a different provider |

**Reading it.** 8 kHz output and mu-law are supported, which suits a real phone line later. Latency is unknown. **Expectation:** first audio in a few hundred milliseconds, to be measured; the long-text and number-reading behaviour needs a test in Hindi and Telugu (rupee amounts, "1.5 kg", phone-style digit strings).

---

### 2.5 End-to-end time to first audio

**Published reference.** A cascaded build with Deepgram, a 7B model on an A10G GPU and ElevenLabs measured **755 ms** end to end; its 947 ms headline figure is only the sum of its stage medians. Stage medians there: recogniser 402 ms, model 457 ms, synthesis 221 ms. That stack waits 700 ms for silence before it starts.

**What our budget looks like (the unknowns are marked)**

| Step | Time | Label |
|---|---|---|
| Wait for end of speech (VAD hangover) | 650 ms | Known (our setting) |
| Prisma finishing the sentence | ? | Unknown |
| Gemini first sentence out (first token plus enough text to end a sentence) | ? | Unknown |
| Timbre first audio chunk | ? | Unknown |
| Network between our server and the cloud services | ? | Unknown |

The known part alone is 650 ms, and the sentence splitter waits for a full sentence before speech starts. The published system also waits for silence and uses a fast local model, and it still lands at 755 ms; ours calls three cloud services over the internet, so I have no reason to expect a lower figure. **Expectation:** roughly 1.5 to 3 s on a normal connection (a hypothesis, built from the sums above and nothing else). If the first Gemini sentence is slow, the optional acknowledgement phrase (method M11 in research_papers.md) is the cheap fix.

---

### 2.6 Rule layer: order totals, stock, credit, loan figures

- **Published:** letting a program do the arithmetic fixes arithmetic errors (PAL). A later paper warns that errors move to interpretation, meaning the wrong item or quantity.
- **Expectation for money:** if the code receives the right item and quantity, the total and EMI are exactly right every time. This is a property of code, not a measured accuracy.
- **Expectation for understanding:** the weak points are (1) mishearing numbers ("dedh lakh", "do sau pachaas", "twenty-five"), (2) mixed-language item names, (3) Telugu quantities. Prisma's `transcribe` format (spoken numbers to digits) may help; test in Hindi and Telugu.
- **Loan calls:** the EMI is only as right as the heard project cost. A mistake there is a confident wrong answer. The agent must read back the amount it heard before computing.

---

### 2.7 Many callers at once

- Gnani's per-organisation cap on simultaneous streaming sessions is **unknown** (docs: shown in the dashboard). Credits: 5,000 on registration (from the brief; verify).
- Timbre: one request at a time per connection, so each call needs its own connection.
- Gemini rate limit: unknown for our key.
- No published system tells us the right design (see research_papers.md, section 7).
- **Expectation:** the cap set by these limits is probably small for a free account, but I have no number. Measure it (experiment E5) before promising any call count.

---

## 3. Targets we will aim for

These are goals set before any run. They may be revised once, after the first full run, and the revision will be written down with the reason.

| Measure | Target | Why this number |
|---|---|---|
| Order accuracy (right items and quantities), clean | At least 90% of orders fully right | Our own goal; no published baseline exists |
| Order accuracy, noisy (about 10 dB) | At least 75% | Our own goal |
| Invented items (not in the stock list) | 0 | Enforced by code; any case is a bug |
| Money errors given correct items | 0 | Enforced by code |
| Time to first audio, median | At most 2.0 s | Budget in 2.5; roughly twice the published 755 ms |
| Callers cut off mid-list | At most 5% of item-list turns | Our own goal |
| Telephone-style WER, Hindi / Telugu | Under 12% / under 18% | **Gnani's own suggested thresholds**, from their benchmarking article; a vendor opinion, not a standard. We may well miss them |

Missing a target is a result and we report it as one.

---

## 4. How we will measure so the numbers can be trusted

Taken from Gnani's benchmarking guide, the Vistaar and IndicVoices papers, and the code-switching paper.

1. **Sample size.** The guide says about 200 utterances per language and condition are enough to shortlist, and about 400 to resolve ±1 point of WER at 95% confidence. Our plan of 20 scripts gives on the order of a hundred and fifty utterances per condition once each script is split, **so our WER figures will have wide error bars.** Report the interval, not only the average, and do not claim small differences.
2. **Report both WER and T-WER** (English words correct in either script) on mixed-language scripts.
3. **Separate sets:** clean, noisy (state the SNR), and 8 kHz when a phone number exists. Use real 8 kHz audio or downsampled audio, say which, and do not call downsampled audio "telephony".
4. **Substitutions, deletions and insertions** reported separately.
5. **Order accuracy is the headline** for the shop calls. WER is a diagnostic.
6. **Time to first audio** measured end to end, from end of the caller's speech to the first audio sample out, not as the sum of stage times (the published tutorial shows the difference).
7. **Cutoff rate and latency reported together.**
8. **Test with and without** `x-keyterms`, and with and without the Prisma context options, because the docs say they can hurt.
9. **State plainly that the callers are synthetic** and that real speech will be harder.

---

## 5. Experiments to run first (cheap, high information)

| # | Experiment | Answers | Needs |
|---|---|---|---|
| E1 | Gemini first-token time with our real prompt | The biggest unknown in the latency budget | Gemini key |
| E2 | Timbre time to first chunk, Hindi / Telugu / mixed, short and long text | Whether synthesis is fast; how it reads rupees and decimals | Gnani key |
| E3 | Prisma on the same script: 16 kHz, 8 kHz downsampled, and 10 dB noise | The size of the telephone penalty on our audio | Gnani key |
| E4 | Prisma with and without `x-keyterms` on item names | Whether product-name boosting helps | Gnani key |
| E5 | Opening many Prisma sessions at once until one is refused | The real concurrency cap | Gnani key |
| E6 | Hindi and Telugu number words ("dedh", "adhai", "sau", "veyyi") through Prisma `transcribe` | The most dangerous failure for money | Gnani key |
| E7 | Check that `commit` closes a segment on v3.0, and how fast the transcript follows | Whether `finish()` can skip the silence wait | Gnani key |

All seven need the keys you have not yet created (app.gnani.ai/voice and Google AI Studio). The smoke-test script in the build plan is these experiments.

---

## 6. Inconsistencies found in the sources

| Where | What disagrees |
|---|---|
| Gnani's product page vs Gnani's benchmarking article | 3.8% vs 26.24% WER on Gramvaani |
| Gnani's quoted latency | "Under 500 ms", "under 200 ms" and "P95 under 200 ms" for different pages |
| Gnani's two Prisma pages | The model page names headers `x-model`, `lang_code`, `x-format`, `x-keyterms`; the WebSocket page names `model`, `language_code`, `format`, `keyterms`. The model page omits `commit`; the WebSocket page documents it |
| Artificial Analysis | The same model's latency changed between page captures (5.77 s, 6.13 s, 6.24 s) |
| Enterprise voice-agent tutorial | 947 ms "measured" in the abstract is an estimate; 755 ms is the measurement |
| Streaming-endpointer paper | Abstract says a 35% reduction; its table gives about 55% |

When two sources disagree, we measure it ourselves and say which source we measured against.

---

## 7. Sources

- Vistaar: [arXiv 2305.15386](https://arxiv.org/pdf/2305.15386), read from the PDF text.
- IndicVoices: [arXiv 2403.01926](https://arxiv.org/html/2403.01926v1), first 100,000 of 149,327 characters read.
- Gnani docs, read 2026-10-28: [Limits](https://docs.gnani.ai/api/STT/limits.md), [Prisma v3.0](https://docs.gnani.ai/api/STT/models/prisma-v3.md), [Realtime TTS](https://docs.gnani.ai/api/TTS/tts-websocket.md), [Changelog](https://docs.gnani.ai/api/introduction/changelog.md).
- Gnani, [how to benchmark an STT API for Indian languages](https://gnani.ai/resources/research/how-to-benchmark-stt-api-indian-languages) (vendor article; its figures are Gnani's own).
- Third-party model latency: [OrcaRouter comparison](https://www.orcarouter.ai/compare/gemini-2.5-flash-lite-vs-gemini-3.6-flash), [Artificial Analysis, Gemini 3.1 Flash-Lite](https://artificialanalysis.ai/models/gemini-3-1-flash-lite-preview/providers).
- All other papers: [research_papers.md](research_papers.md).
