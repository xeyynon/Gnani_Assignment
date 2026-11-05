# Plan: retrieval (RAG) in Dukaan Dost

**Written 2026-11-03.** What retrieval-augmented generation means for this project, what we measured, what is built, and what comes next. Rule R-5 applies: every figure below is from a saved run or the benchmark named next to it.

## 1. What problem retrieval solves here
The model must know the shop: its products, its policies (delivery, payment, hours). It cannot hold all of it in every prompt forever, so something must choose what to show it each turn. That choice is retrieval; showing the chosen text to the model is the "augmented generation".

There are two different kinds of shop knowledge, and they need different treatment:

| Kind | Example | Size now | Who needs it right |
|---|---|---|---|
| **Products** | "pyaz", "प्याज", "ఉల్లిపాయలు" are all ONION-1KG | 61 items | The order code: a missed product is a wrong order |
| **Shop facts** | "delivery within 3 km", "UPI ID", opening hours | 8 short files | The caller's questions: a missed fact is a vague answer |

## 2. What we had, and what it cost us
The first valid evaluation (B-34, `evaluation/results/orders_clean_baseline_retrieval.*`, 20 calls, gpt-oss-120b) got **9 of 20 orders exactly right**. Eight of the 11 wrong orders came from retrieval: the model was shown too few product sections, did not see the item, and told the caller "we do not have onions". The cause was the keyword search (whole-word match over product sections, 1,200-character budget): a Hindi spelling with or without the dot under the letter, a Telugu plural, a mis-heard word or a crowd of oils missed the product.

## 3. What we did about it (built, 2026-11-03)
| Step | What | Evidence |
|---|---|---|
| **Catalogue in the prompt** (DEC-042) | Every order turn carries one short line per item: SKU, English, Hindi, Telugu name, unit. No search needed | 6 of 6 failing phrases now give the right order on the live model; costs about 3,200 tokens a turn |
| **Product search** (`product_search.py`, DEC-043) | Character n-gram match of the caller's words against each name and spelling, no model, no network, about 3 ms | See section 4 |
| **Catalogue modes** (`ORDER_CATALOGUE=full\|search\|auto`) | `full` sends all items; `search` sends the best 12 matches plus what is already ordered; `auto` (default) sends all while the catalogue is under 6,000 characters, then switches to search | 3,397 characters in full mode, 324 in search mode on a typical sentence; auto switches on a 366-item test shop |
| **Shop facts** | The existing keyword search, now with everyday words ignored and name matches weighted, no longer including product sections on order turns | `tests/test_knowledge_retriever.py` |

## 4. How good is the product search? (`evaluation/retrieval_benchmark.py`, saved in `evaluation/results/retrieval_benchmark.json`)
76 phrases asking for 133 items: 23 real Prisma outputs from the evaluation, 28 hand-written variants, 24 held out (written after the search was tuned, never used to tune it). No model, no tokens.

| Method | Item recall | Phrases fully covered | Items returned per phrase | Held-out recall |
|---|---|---|---|---|
| Existing keyword search | 0.895 | 64/76 | 4.2 | 0.87 |
| N-gram search, top 3 | 0.977 | 73/76 | 2.5 | 1.00 |
| N-gram search, top 5 | 0.992 | 75/76 | 3.3 | 1.00 |
| N-gram search, top 8 | **1.000** | **76/76** | 3.6 | 1.00 |

**Read this with care:**
- The 76 phrases are few, and the shop's own Hindi and Telugu names are in the search index, so the held-out phrases are easier than a real caller's. Treat 1.000 as "no failure found", not as a guarantee.
- The search has **false positives**: "cash, my name is Ramesh" returns salt at 0.50. Real hits have median score 1.00, false hits 0.51, but the ranges overlap (a cut at 0.6 keeps 95 percent of real hits and drops 77 percent of false ones). So it **only offers candidates; the model decides**, and the order code still checks every SKU against the stock list.
- Not measured: how Prisma's mistakes behave on real (non-synthetic) voices; shops with hundreds of items whose names are similar.

## 5. Decision rule: catalogue or search?
| Situation | Use | Why |
|---|---|---|
| Up to about 80 items (this shop) | **Full catalogue** | The model sees everything; nothing can be missed; about 1,100 extra tokens a turn |
| Hundreds of items | **Search**, 12 candidates | The catalogue no longer fits the budget; search recall was 1.000 at top 8 on this set |
| Any size, accuracy first | Search plus a second check (not built, section 8) | Catches the false negative the search could still have |
The default `auto` follows this table by size alone. It was not chosen by an end-to-end comparison yet (section 6).

## 6. What is still to measure (needs model tokens, so it waits for the quota)
Groq allows about one full evaluation run per model per day (B-33). Planned, in order:
1. **Catalogue run, clean** (gpt-oss-20b, after its quota recovers about 16:00 on Nov 3): the headline number with all fixes.
2. **Noisy run** at about 10 dB (gpt-oss-120b, the morning of Nov 4).
3. **Search-mode run, clean** (`ORDER_CATALOGUE=search`): the same 20 calls with candidates only. If its order accuracy is within the catalogue run's interval, "search scales without losing accuracy" is a result we can state; if not, the README says so.
Each run is saved to `evaluation/results/`; the README quotes only those.

## 7. Embeddings: considered, not used
A vector model (a "real" RAG) would match meaning, not letters, and would help for synonyms ("cooking oil" for sunflower oil) and for long FAQ text.

| Option | Verdict |
|---|---|
| Gnani | Offers speech models only: no text embeddings |
| Groq | No embeddings endpoint on this account |
| Gemini embeddings | Good multilingual quality; **needs a Gemini key** (none yet); adds a network call to every turn |
| A local model (for example a small multilingual sentence model) | Needs torch and a model download, hundreds of MB; slow to start; not installable in this environment without adding heavy dependencies |

**Decision:** not now. The character search already reaches 1.000 on the test set and runs in 3 ms with no dependency. Revisit if (a) a Gemini key arrives and (b) the benchmark grows a category of phrases where the character search clearly fails (for example synonyms), or (c) a shop has long free-text knowledge.

## 8. Next steps
| # | Task | When | Needs |
|---|---|---|---|
| R1 | Grow `retrieval_cases.py` with every product phrase seen in later evaluation runs, including the ones Prisma garbles | with each run | nothing |
| R2 | Catalogue run, then search-mode run, scored and saved (section 6) | Nov 3 to 4 | model quota |
| R3 | Shop facts: measure how often a policy question gets the right section (a small question set: delivery, payment, hours, returns) | Nov 4 | nothing for retrieval, tokens for the answer |
| R4 | A second check after the model answers: if the model said "not sold" for a phrase whose best search match scores at least 0.9, ask again with that candidate listed | Nov 5, only if the runs show wrongly refused items | none |
| R5 | A hybrid with Gemini embeddings | only after section 7's conditions | Gemini key |
| R6 | README section: the problem, the before and after table, the caveats above | Nov 6 | saved runs |

## 9. Risks
| Risk | Effect | Response |
|---|---|---|
| The search offers the wrong candidates and the model trusts them | A wrong item added | The order code only accepts SKUs in the stock list; the read-back lets the caller correct; the evaluation counts it |
| The catalogue costs tokens that Groq's daily limit cannot afford | Fewer evaluation runs | `search` mode cuts the prompt by about 90 percent for the products part; runs are planned, not repeated |
| The test set is too friendly | An overstated recall | Say so (section 4); keep adding Prisma's real errors |
| A bigger shop breaks `auto` | Unknown | The mode is a setting; the benchmark runs on any `stock.json` in seconds |

## 10. Files
`dukaan_dost/product_search.py` (the search), `dukaan_dost/stock.py` (`catalogue_text`), `dukaan_dost/conversation_manager.py` (`catalogue_for`, modes), `dukaan_dost/knowledge_retriever.py` (shop facts), `evaluation/retrieval_cases.py` and `evaluation/retrieval_benchmark.py` (the test), `tests/test_product_search.py`, `tests/test_knowledge_retriever.py`.
