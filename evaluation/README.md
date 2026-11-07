# Evaluation

Tools that measure the agent. Run them from the project root.

## Scripted calls through the real agent
Synthetic callers (Timbre voices) phone the **real** agent, with no browser: the voice detector, Prisma, the language model, the order code and Timbre all run. A replay transport (`dukaan_dost/transport_replay.py`) plays each turn of each call, waits for the reply, and records what happened.

```bash
python evaluation/run_calls.py evaluation/scripts/orders.json --out evaluation/audio/run_clean.json
python evaluation/run_calls.py evaluation/scripts/orders.json --noise 10 --out evaluation/audio/run_noisy.json   # steady synthetic noise mixed in
python evaluation/score_calls.py evaluation/audio/run_clean.json --out evaluation/results/orders_clean.json
```
- `scripts/orders.json`: 20 order calls, 65 turns, in Hindi, Telugu, English and Hinglish: fractions, changes, removals, brands, out-of-stock items, credit. Each call has the order it should end with.
- `scripts/credit_loans.json`: 4 loan calls (the expected project cost, loan and instalment come from the calculator) and 4 udhaar calls (approved, over the limit, unknown name, balance question).
- `scripts/smoke.json`: a short call to check the loop works.
- The runner starts `python -m dukaan_dost` with `AUDIO_TRANSPORT=replay`, writes the orders to a throwaway folder, and records the model and provider read from the agent's own log.
- The language model has a daily token limit. A run in which any request was refused is marked **INVALID** by the scorer and must not be quoted; so is a run that did not finish every call, or whose agent log is missing.

What the scorer reports (`score_calls.py`):
| Measure | Meaning |
|---|---|
| Orders exactly right | the saved order has exactly the expected items and quantities (and the expected payment, status and balance, where the script says so); 95% interval shown |
| Item recall / precision | expected items found / items in the order that were expected |
| Totals equal the stock-list arithmetic | each saved total recomputed from the stock list |
| Time to first audio | from the caller's **last word** (the silence at the end of the clip is added back) to the first sound of the reply; the figure measured from the end of the file is shown beside it |
| WER | the recogniser's text against the words spoken, raw and with spoken numbers counted as digits |
| T-WER | of the English (Latin-script) words spoken, the share the recogniser missed; a word is right if it came back in Latin letters or as the Hindi or Telugu name that identifies the same product |
| Cut-off | turns split into pieces by the end-of-speech detector, turns with under half the words heard, agent replies the caller's speech cut short when no interruption was scripted |
| Loan calls | scored separately (project cost, loan and instalment against the calculator); they do not count in the order figures |

Noise level: the requested SNR is relative to the whole-clip RMS of the speech clips of the full script, not to the loudest samples. Results taken before 2026-11-05 used a different convention and say so.

## Retrieval benchmark
`python evaluation/retrieval_benchmark.py` compares the old keyword search with the n-gram product search on phrases in the three languages (no model tokens used); the cases are in `retrieval_cases.py` and the result is saved in `results/retrieval_benchmark.json`.

## Older tools inherited from the earlier project
```bash
python -m evaluation.run_benchmark          # Google STT v2 round trip on benchmark_dataset.json
python -m evaluation.analyze_benchmark      # summarises evaluation/results/benchmark_results.json
python -m evaluation.stt_regression_test    # replays captured call audio through the active STT provider
python -m evaluation.profile_frame_cost     # CPU cost of the per-frame audio work
```
`benchmark_dataset.json` is the generic 60-question set from the earlier project; it is not used for any Dukaan Dost figure.

## Where things go
- `results/` is committed. Every number in the README, the videos and the posts must come from a saved run there (rule R-5).
- `audio/` (generated speech, raw run files, agent logs) is not committed.

## Running a whole evaluation on a frozen copy
`python evaluation/run_snapshot.py --runs search20b` copies the working folder, puts every tracked file back to its committed state, runs the listed runs from that copy, scores them and saves the results in `evaluation/results/` (a run in which the model refused any request, or that did not finish, is saved with an `INVALID_` or `INCOMPLETE_` prefix and is never quoted). Run names are in the script; `smoke` (two calls) checks the set-up first. The copy means fixes made while a run goes cannot change what it measures. A model's daily token limit is about one full 20-call run, so give a model one full run a day and nothing else; `--min-turn-sec` (28 by default) keeps a run under the per-minute limit. The Prisma-alone accuracy script is `python evaluation/stt_accuracy.py --out evaluation/results/stt_accuracy_prisma`.
