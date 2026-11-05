# run_clean_5: clean

Model: openai/gpt-oss-20b. Synthetic Timbre speech; 20 scripted order calls, 65 turns.

**INVALID RUN: the language model refused 8 requests (rate limit or quota). Do not quote these figures.**

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | 13/20 (65%; 95% interval 43% to 82%) |
| Item recall / precision (orders only) | 1.00 / 0.97 |
| Payment chosen correctly (orders only) | 15/20 |
| Totals equal to the stock-list arithmetic | 20/20 |
| Time to first audio from the caller's last word, median / 90th percentile | 3836 ms / 5200 ms (n=65) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 3453 ms / 4872 ms (n=65) |
| Turns with no reply | 0/65 |
| Word error rate, raw / number-normalised | 0.464 / 0.334 (293 words) |
| T-WER (English words missed) | 0.492 (195 English words) |
| Cut-off: turns split into pieces / under half the words heard | 2/63 / 0/63 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| en-IN | 4 | 3 (75%) | 1.00 | 0.88 |
| hi-IN | 3 | 2 (67%) | 1.00 | 1.00 |
| hi-en | 8 | 4 (50%) | 1.00 | 1.00 |
| te-IN | 5 | 4 (80%) | 1.00 | 1.00 |

| Kind of call (order calls) | Calls | Exact |
|---|---|---|
| brands | 1 | 0 (0%) |
| change | 4 | 3 (75%) |
| credit | 3 | 2 (67%) |
| english | 4 | 3 (75%) |
| fractions | 5 | 4 (80%) |
| hindi | 3 | 2 (67%) |
| hinglish | 8 | 4 (50%) |
| not_sold | 2 | 1 (50%) |
| out_of_stock | 3 | 1 (33%) |
| removal | 2 | 1 (50%) |
| telugu | 5 | 4 (80%) |

Calls not exactly right:

- h02: missing [], extra [], wrong quantities {'MAGGI-70': [1.0, 2.0], 'PARLEG-100': [2.0, 3.0], 'BUTTER-100': [1.0, 2.0]}
- h04: missing [], extra [], wrong quantities {'RICE-1KG': [2.0, 1.0]}
- h06: missing [], extra [], wrong quantities {'BREAD-400': [1.0, 2.0]}
- h07: missing [], extra [], wrong quantities {'MAGGI-70': [2.0, 6.0]}
- d01: missing [], extra [], wrong quantities {'ATTA-5KG': [2.0, 4.0], 'OIL-1L': [1.0, 16.0]}
- t02: missing [], extra [], wrong quantities {'ONION-1KG': [0.5, 1.0]}
- e04: missing [], extra ['EGGS-6'], wrong quantities {}
