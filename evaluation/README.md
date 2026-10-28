# Evaluation

Tools that measure the agent. Run them from the project root, as modules:

```bash
python -m evaluation.run_benchmark          # Google STT v2 round trip on benchmark_dataset.json
python -m evaluation.analyze_benchmark      # summarises evaluation/results/benchmark_results.json
python -m evaluation.stt_regression_test    # replays captured call audio through the active STT provider
python -m evaluation.profile_frame_cost     # CPU cost of the per-frame audio work (run it on the machine that will run the demo)
```

- `benchmark_dataset.json` is the 60-question generic set inherited from the
  earlier project. It will be replaced by order and loan-guidance scripts (see
  `MD/tasks.md`, build step 9).
- Results land in `evaluation/results/`, which is committed. Every number in the
  README must come from a saved run there (rule R-5).
- Generated audio goes in `evaluation/audio/`, which is not committed.
