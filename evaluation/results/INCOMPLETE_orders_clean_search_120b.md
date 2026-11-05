# run_clean_search_120b_1: clean

Model: openai/gpt-oss-120b (Groq). Synthetic Timbre speech; 15 scripted order calls, 47 turns.

**INCOMPLETE RUN: 15 of 20 scripted calls finished and the run never reached its done flag (missing: t05, e01, e02, e03, e04). Do not quote these figures.**

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | 1/15 (7%; 95% interval 1% to 30%) |
| Item recall / precision (orders only) | 0.07 / 0.07 |
| Payment chosen correctly (orders only) | 0/15 |
| Totals equal to the stock-list arithmetic | 1/1 |
| Time to first audio from the caller's last word, median / 90th percentile | 2739 ms / 3876 ms (n=3) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 2079 ms / 3616 ms (n=3) |
| Turns with no reply | 44/47 |
| Word error rate, raw / number-normalised | 0.995 / 0.985 (202 words) |
| T-WER (English words missed) | 0.982 (112 English words) |
| Cut-off: turns split into pieces / under half the words heard | 0/3 / 0/3 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| hi-IN | 3 | 0 (0%) | 0.00 | 0.00 |
| hi-en | 8 | 1 (12%) | 0.12 | 0.12 |
| te-IN | 4 | 0 (0%) | 0.00 | 0.00 |

| Kind of call (order calls) | Calls | Exact |
|---|---|---|
| brands | 1 | 0 (0%) |
| change | 3 | 0 (0%) |
| credit | 2 | 0 (0%) |
| fractions | 4 | 0 (0%) |
| hindi | 3 | 0 (0%) |
| hinglish | 8 | 1 (12%) |
| not_sold | 1 | 0 (0%) |
| out_of_stock | 1 | 0 (0%) |
| removal | 1 | 0 (0%) |
| telugu | 4 | 0 (0%) |

Calls not exactly right:

- h02: missing ['BUTTER-100', 'MAGGI-70', 'PARLEG-100'], extra [], wrong quantities {} (no order saved)
- h03: missing ['ONION-1KG', 'POTATO-1KG'], extra [], wrong quantities {} (no order saved)
- h04: missing ['DAL-TOOR-1KG', 'RICE-1KG'], extra [], wrong quantities {} (no order saved)
- h05: missing ['GHEE-500'], extra [], wrong quantities {} (no order saved)
- h06: missing ['BREAD-400'], extra [], wrong quantities {} (no order saved)
- h07: missing ['MAGGI-70'], extra [], wrong quantities {} (no order saved)
- h08: missing ['SUGAR-1KG'], extra [], wrong quantities {} (no order saved)
- d01: missing ['ATTA-5KG', 'OIL-1L'], extra [], wrong quantities {} (no order saved)
- d02: missing ['SUGAR-1KG', 'TEA-250'], extra [], wrong quantities {} (no order saved)
- d03: missing ['BASMATI-1KG', 'TOMATO-1KG'], extra [], wrong quantities {} (no order saved)
- t01: missing ['OIL-1L', 'RICE-1KG'], extra [], wrong quantities {} (no order saved)
- t02: missing ['ONION-1KG', 'POTATO-1KG'], extra [], wrong quantities {} (no order saved)
- t03: missing ['SUGAR-1KG', 'TEA-250'], extra [], wrong quantities {} (no order saved)
- t04: missing ['DAL-TOOR-1KG', 'SOAP-100'], extra [], wrong quantities {} (no order saved)
