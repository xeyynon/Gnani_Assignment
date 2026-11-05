# run_credit_loans_1: clean

Model: openai/gpt-oss-120b (Groq). Synthetic Timbre speech; 0 scripted order calls and 4 loan calls, 6 turns.

**INCOMPLETE RUN: 4 of 8 scripted calls finished and the run never reached its done flag (missing: U01, U02, U03, U04). Do not quote these figures.**

| Measure | Result |
|---|---|
| Orders exactly right (items and quantities; loan calls not included) | no calls |
| Item recall / precision (orders only) | no order calls |
| Payment chosen correctly (orders only) | 0/0 |
| Loan calls: exact | 4/4 (100%; 95% interval 51% to 100%) |
| Totals equal to the stock-list arithmetic | 0/0 |
| Time to first audio from the caller's last word, median / 90th percentile | 3466 ms / 4435 ms (n=6) |
| Time to first audio from the end of the audio file (uncorrected: the clips end with a pause, so this is too small) | 3172 ms / 4235 ms (n=6) |
| Turns with no reply | 0/6 |
| Word error rate, raw / number-normalised | None / None (0 words) |
| T-WER (English words missed) | None (0 English words) |
| Cut-off: turns split into pieces / under half the words heard | 0/0 / 0/0 |
| Agent clips the caller cut short with no interruption scripted | 0 |

| Language | Calls | Exact | Recall | Precision |
|---|---|---|---|---|

| Kind of call (order calls) | Calls | Exact |
|---|---|---|

Calls not exactly right:

