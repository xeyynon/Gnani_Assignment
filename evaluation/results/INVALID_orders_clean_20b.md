# run_clean_20b_2: clean

Model: openai/gpt-oss-20b (Groq). Synthetic Timbre speech; 20 scripted order calls, 65 turns.

**INVALID RUN: the language model refused 7 requests (rate limit or quota). Do not quote these figures.**

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | 16/20 (80%; 95% interval 58% to 92%) |
| Item recall / precision (orders only) | 0.93 / 0.93 |
| Payment chosen correctly (orders only) | 13/20 |
| Totals equal to the stock-list arithmetic | 19/19 |
| Time to first audio from the caller's last word, median / 90th percentile | 2465 ms / 3059 ms (n=65) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 2140 ms / 2732 ms (n=65) |
| Turns with no reply | 0/65 |
| Word error rate, raw / number-normalised | 0.464 / 0.334 (293 words) |
| T-WER (English words missed) | 0.492 (195 English words) |
| Cut-off: turns split into pieces / under half the words heard | 2/63 / 0/63 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| en-IN | 4 | 3 (75%) | 1.00 | 0.88 |
| hi-IN | 3 | 2 (67%) | 0.67 | 0.67 |
| hi-en | 8 | 7 (88%) | 0.94 | 1.00 |
| te-IN | 5 | 4 (80%) | 1.00 | 1.00 |

| Kind of call (order calls) | Calls | Exact |
|---|---|---|
| brands | 1 | 1 (100%) |
| change | 4 | 4 (100%) |
| credit | 3 | 2 (67%) |
| english | 4 | 3 (75%) |
| fractions | 5 | 4 (80%) |
| hindi | 3 | 2 (67%) |
| hinglish | 8 | 7 (88%) |
| not_sold | 2 | 2 (100%) |
| out_of_stock | 3 | 2 (67%) |
| removal | 2 | 1 (50%) |
| telugu | 5 | 4 (80%) |

Calls not exactly right:

- h01: missing ['SUGAR-1KG'], extra [], wrong quantities {}
- d01: missing ['ATTA-5KG', 'OIL-1L'], extra [], wrong quantities {} (no order saved)
- t02: missing [], extra [], wrong quantities {'ONION-1KG': [0.5, 1.0]}
- e04: missing [], extra ['EGGS-6'], wrong quantities {}
