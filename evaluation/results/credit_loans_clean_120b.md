# run_credit_loans: clean

Model: openai/gpt-oss-120b (Groq). Synthetic Timbre speech; 4 scripted order calls and 4 loan calls, 18 turns.

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | 4/4 (100%; 95% interval 51% to 100%) |
| Item recall / precision (orders only) | 1.00 / 1.00 |
| Payment chosen correctly (orders only) | 4/4 |
| Loan calls: exact | 4/4 (100%; 95% interval 51% to 100%) |
| Totals equal to the stock-list arithmetic | 3/3 |
| Time to first audio from the caller's last word, median / 90th percentile | 2196 ms / 2471 ms (n=18) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 1828 ms / 2276 ms (n=18) |
| Turns with no reply | 0/18 |
| Word error rate, raw / number-normalised | 0.474 / 0.404 (57 words) |
| T-WER (English words missed) | 0.456 (57 English words) |
| Cut-off: turns split into pieces / under half the words heard | 0/12 / 0/12 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|
| en-IN | 2 | 2 (100%) | 1.00 | 1.00 |
| hi-en | 2 | 2 (100%) | 1.00 | 1.00 |

| Kind of call (order calls) | Calls | Exact |
|---|---|---|
| approved | 1 | 1 (100%) |
| balance | 1 | 1 (100%) |
| credit | 4 | 4 (100%) |
| over_limit | 1 | 1 (100%) |
| unknown_name | 1 | 1 (100%) |

Calls not exactly right:

