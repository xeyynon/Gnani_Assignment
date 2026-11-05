> **Baseline, taken 2026-11-03 BEFORE the catalogue fix (DEC-042) and the self-echo fix (B-36).** Order matching used keyword search over product sections. Kept so the README can show the before and after. Model: gpt-oss-120b. The run before this one (gpt-oss-20b) was thrown away: the model's daily token limit ran out partway through (B-33).

# run_clean_4: clean

Model: openai/gpt-oss-120b. Synthetic Timbre speech; 20 scripted calls, 65 turns.

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities) | 9/20 (45%; 95% interval 26% to 66%) |
| Item recall / precision | 0.75 / 0.95 |
| Payment chosen correctly | 17/20 |
| Totals equal to the stock-list arithmetic | 20/20 |
| Time to first audio, median / 90th percentile | 2352 ms / 2860 ms (n=62) |
| Turns with no reply | 3/65 |
| Word error rate, raw / number-normalised | 0.41 / 0.287 (293 words) |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| en-IN | 4 | 3 (75%) | 0.88 | 1.00 |
| hi-IN | 3 | 0 (0%) | 0.67 | 1.00 |
| hi-en | 8 | 5 (62%) | 0.75 | 0.88 |
| te-IN | 5 | 1 (20%) | 0.70 | 1.00 |

| Kind of call | Calls | Exact |
|---|---|---|
| brands | 1 | 1 (100%) |
| change | 4 | 1 (25%) |
| credit | 3 | 2 (67%) |
| english | 4 | 3 (75%) |
| fractions | 5 | 0 (0%) |
| hindi | 3 | 0 (0%) |
| hinglish | 8 | 5 (62%) |
| not_sold | 2 | 2 (100%) |
| out_of_stock | 3 | 3 (100%) |
| removal | 2 | 2 (100%) |
| telugu | 5 | 1 (20%) |

Calls not exactly right:

- h01: missing ['SUGAR-1KG'], extra [], wrong quantities {}
- h03: missing ['ONION-1KG'], extra [], wrong quantities {}
- h08: missing ['SUGAR-1KG'], extra ['OIL-1L'], wrong quantities {}
- d01: missing ['ATTA-5KG'], extra [], wrong quantities {'OIL-1L': [1.0, 8.0]}
- d02: missing ['TEA-250'], extra [], wrong quantities {}
- d03: missing [], extra [], wrong quantities {'TOMATO-1KG': [1.0, 0.5]}
- t01: missing ['OIL-1L'], extra [], wrong quantities {}
- t02: missing ['POTATO-1KG'], extra [], wrong quantities {}
- t03: missing [], extra [], wrong quantities {'SUGAR-1KG': [2.0, 3.0]}
- t04: missing ['SOAP-100'], extra [], wrong quantities {}
- e03: missing ['ONION-1KG'], extra [], wrong quantities {}
