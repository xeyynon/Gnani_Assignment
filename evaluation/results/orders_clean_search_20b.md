# run_search_20b: clean

Model: openai/gpt-oss-20b (Groq). Synthetic Timbre speech; 20 scripted order calls, 65 turns.

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | 18/20 (90%; 95% interval 70% to 97%) |
| Item recall / precision (orders only) | 1.00 / 1.00 |
| Payment chosen correctly (orders only) | 16/20 |
| Totals equal to the stock-list arithmetic | 20/20 |
| Time to first audio from the caller's last word, median / 90th percentile | 2151 ms / 2746 ms (n=64) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 1867 ms / 2435 ms (n=64) |
| Turns with no reply | 1/65 |
| Word error rate, raw / number-normalised | 0.464 / 0.331 (293 words) |
| T-WER (English words missed) | 0.503 (195 English words) |
| Cut-off: turns split into pieces / under half the words heard | 0/63 / 1/63 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| en-IN | 4 | 4 (100%) | 1.00 | 1.00 |
| hi-IN | 3 | 2 (67%) | 1.00 | 1.00 |
| hi-en | 8 | 8 (100%) | 1.00 | 1.00 |
| te-IN | 5 | 4 (80%) | 1.00 | 1.00 |

| Kind of call (order calls) | Calls | Exact |
|---|---|---|
| brands | 1 | 1 (100%) |
| change | 4 | 4 (100%) |
| credit | 3 | 3 (100%) |
| english | 4 | 4 (100%) |
| fractions | 5 | 4 (80%) |
| hindi | 3 | 2 (67%) |
| hinglish | 8 | 8 (100%) |
| not_sold | 2 | 2 (100%) |
| out_of_stock | 3 | 3 (100%) |
| removal | 2 | 2 (100%) |
| telugu | 5 | 4 (80%) |

Calls not exactly right:

- d01: missing [], extra [], wrong quantities {'OIL-1L': [1.0, 8.0]}
- t02: missing [], extra [], wrong quantities {'ONION-1KG': [0.5, 1.0]}
