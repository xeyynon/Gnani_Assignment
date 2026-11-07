# Hand-over: 2026-11-05 (evening)

Read [DukaanDost_MASTER.md](DukaanDost_MASTER.md) for the status and [poa_nov5_to_9.md](poa_nov5_to_9.md) for the plan to submission. This note says what happened tonight, what is proven, and what to do next.

## What changed
- **Build 1013** (`e8cde76`; it had one serious regression, B-86, fixed in Build 1014): about 30 defects fixed in the agent, found by five parallel bug finders and by reading the logs of the first valid evaluation run. The big ones: the model copying earlier items into later turns (B-82, it doubled orders), a damaged udhaar ledger replaced by opening balances (B-41), the customer charged before the order was saved (B-66), ordinary shop talk starting the sticky loan mode (B-46), a new customer matched to a similar known name (B-47), a call outliving its hang-up leaking into the next (B-64), a quiet Timbre connection stalling a sentence (B-50), and the phone provider being sent the caller's words (B-62).
- **InBul21**: the evaluation harness made honest (time to first audio from the caller's last word, noise level, truncated runs, loan calls scored apart: B-56 to B-61, B-63, B-72 to B-75, B-84), plus the README rewrite, the plan, the submission drafts, `bugfixed.md` and the saved evidence runs.
- Every fix is listed with its proof in [bugfixed.md](bugfixed.md); the story of each is in [bugs.md](bugs.md).

## What is proven, and how
- 1,138 Python tests and 102 page tests pass; the local CI copy passes lint, the Python 3.10 check and the package check (the Docker step needs Docker running). It found one real failure that GitHub's CI would have shown: a test secret in a tracked file (B-80).
- A short live call (real Prisma, model and Timbre) runs end to end with the fixes in. Inside the agent the first Timbre sentence now takes about 0.8 s instead of about 2 s (B-81, measured on the live service).

## What is not proven
- **No valid evaluation score exists after the fixes.** The three runs of Nov 5 are saved as evidence only: the 20b run is INVALID (the model's daily token limit, B-33), the credit/loan run INCOMPLETE (the laptop slept 26 minutes, B-84), the noisy run INCOMPLETE and nothing was understood at 10 dB steady noise (B-85). Do not quote them.
- Whether the repeat guard (B-82) is enough, and what the pipeline scores now: wait for the valid runs below.
- The browser call has still not been used by a person with a microphone.

## What is running or due
- **Valid, saved:** `credit_loans_clean_120b` (2026-11-06 01:06, Build 1014 code, gpt-oss-120b): 4 of 4 order calls and 4 of 4 loan calls exactly right, 0 of 18 turns without a reply, no rate limit. Only 8 calls, so the interval is wide (51% to 100%).
- **Evidence only:** `INVALID_orders_clean_search_120b` (2026-11-06 01:15, search mode, gpt-oss-120b): 16 of 20 orders exact, but the model refused 3 requests in the last call (e04, the daily limit), so it is INVALID and may not be quoted. Of the 3 other wrong calls, 2 were hearing (B-24 again: "ek litre" heard as "8 litre"; Telugu "అర కిలో" heard as "కిలో") and 1 was the model (t04: kandipappu mapped to urad dal). The run no longer shows the repeat-of-earlier-changes failure (B-82).
- Due **Nov 6 from about 21:30**: the default-mode clean run on gpt-oss-20b (the model's window will have emptied). One full run per model per 24 hours, in a rolling window. The 120b budget is now spent for the day.
- Then: noise at 20 dB and 15 dB (B-85).

## Pitfalls learned tonight
- **Build 1013 broke every call after the first (B-86), fixed in Build 1014.** The live check before the commit ran one call. Always run two or more calls (`evaluation/scripts/smoke.json` now has two) before calling a change to the call lifecycle done.
- The model's daily token limit is a rolling 24 hours; a run that gets no replies costs almost no tokens.
- A laptop that sleeps freezes a run; `run_calls.py` now asks Windows to stay awake.
- Do not run heavy work (the test suite) at normal priority beside a run if its timing matters.
- A tracked file that quotes a key-shaped string fails `check_repo.py`; untracked files are not checked, so run it after `git add`.
- Two sessions share one working tree and one checked-out branch (`frontend-audit` at the time of writing); each commits only its own files.

## Next, in order
1. Build 1014 (B-86) first. Then repeat the search-mode run on gpt-oss-120b if its budget allows, and the default-mode run on gpt-oss-20b from about 21:30 on Nov 6.
2. Nov 6 evening: the default-mode run on gpt-oss-20b; read the wrong orders; fix the top causes.
3. Surya: a real call in Chrome with a microphone (the demo video is this call), the phone decision, the loan figures, the native-speaker check, and the posts (due about Nov 5).
4. Fill the README results block only from valid runs; update `submission_drafts.md` blanks.
