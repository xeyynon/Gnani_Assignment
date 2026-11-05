# run_clean_search_120b_2: clean

Model: openai/gpt-oss-120b (Groq). Synthetic Timbre speech; 20 scripted order calls, 65 turns.

**INVALID RUN: the language model refused 3 requests (rate limit or quota). Do not quote these figures.**

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | 16/20 (80%; 95% interval 58% to 92%) |
| Item recall / precision (orders only) | 0.95 / 0.95 |
| Payment chosen correctly (orders only) | 15/20 |
| Totals equal to the stock-list arithmetic | 20/20 |
| Time to first audio from the caller's last word, median / 90th percentile | 2387 ms / 3182 ms (n=65) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 2110 ms / 2854 ms (n=65) |
| Turns with no reply | 0/65 |
| Word error rate, raw / number-normalised | 0.464 / 0.334 (293 words) |
| T-WER (English words missed) | 0.492 (195 English words) |
| Cut-off: turns split into pieces / under half the words heard | 2/63 / 0/63 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| en-IN | 4 | 3 (75%) | 1.00 | 0.88 |
| hi-IN | 3 | 2 (67%) | 0.83 | 1.00 |
| hi-en | 8 | 8 (100%) | 1.00 | 1.00 |
| te-IN | 5 | 3 (60%) | 0.90 | 0.90 |

| Kind of call (order calls) | Calls | Exact |
|---|---|---|
| brands | 1 | 1 (100%) |
| change | 4 | 4 (100%) |
| credit | 3 | 1 (33%) |
| english | 4 | 3 (75%) |
| fractions | 5 | 4 (80%) |
| hindi | 3 | 2 (67%) |
| hinglish | 8 | 8 (100%) |
| not_sold | 2 | 2 (100%) |
| out_of_stock | 3 | 2 (67%) |
| removal | 2 | 1 (50%) |
| telugu | 5 | 3 (60%) |

Calls not exactly right:

- d01: missing ['ATTA-5KG'], extra [], wrong quantities {'OIL-1L': [1.0, 8.0]}
- t02: missing [], extra [], wrong quantities {'ONION-1KG': [0.5, 1.0]}
- t04: missing ['DAL-TOOR-1KG'], extra ['DAL-URAD-1KG'], wrong quantities {}
- e04: missing [], extra ['EGGS-6'], wrong quantities {}
