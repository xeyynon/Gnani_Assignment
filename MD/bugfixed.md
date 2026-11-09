# Bugs fixed: the log

A dated log of every fix, newest first. [bugs.md](bugs.md) is the register (what each bug was, why it mattered, what is still open); this file answers "what was fixed when, how do we know, and where is it". One line per fix; add the line in the same change that fixes the bug, with its regression test. The build or InBul id is filled in when the fix ships.

| Date | Bug | Fix | Proof (test or run) | Commit | Build or InBul |
|---|---|---|---|---|---|
| 2026-11-09 | B-100 | A bare English payment word keeps a Hindi or Telugu call in its language | `tests/test_lifecycle_fixes.py` | cdbcbef | Build 1023 |
| 2026-11-09 | B-99 | A that-is-all at the end of a sentence with an item closes the list even if the model misses it | `tests/test_order_turn.py` | cdbcbef | Build 1023 |
| 2026-11-09 | B-98 | After the payment a thank-you gets a short thanks, not the order read again | `tests/test_order_turn.py` | cdbcbef | Build 1023 |
| 2026-11-09 | B-97 | A missed word at the payment step is asked for by name, in the caller's language | `tests/test_lifecycle_fixes.py`, three tests | d2c527c | Build 1021 |
| 2026-11-08 | B-96 | Only Telugu is named to Prisma; naming Hindi kept a Telugu call decoded as Hindi (loan call L02 lost) | `tests/test_lifecycle_fixes.py`; rerun `credit_loans_clean_120b` (4 of 4 loans) | 10efdf8 | Build 1019 |
| 2026-11-08 | B-95 | The replay transport's close() waits for the final results file, so a caller no longer reads it mid-write (a flaky Windows test) | `tests/test_transport_replay.py`, repeated runs in a clean environment | InBul36 | InBul36 |
| 2026-11-07 | B-94 | A Hindi or Telugu call names its language to Prisma from the second turn (Telugu 10 of 16 exact against 5 of 16) | `evaluation/results/stt_accuracy_prisma`; `tests/test_lifecycle_fixes.py` | a439851 | Build 1016 |
| 2026-11-07 | B-93 | An empty turn is heard again with the language named (8 of 8 problem clips recovered against 1 of 8) | `tests/test_lifecycle_fixes.py`, four tests; synthetic-clip experiment in bugs.md | a439851 | Build 1016 |
| 2026-11-07 | B-92 | The demo shop sells atta loose by the kilo and in 5 and 10 kg bags | `tests` pass (1,220); retrieval benchmark 76 of 76 at top 8 | a439851 | Build 1016 |
| 2026-11-07 | B-91 | A silent, no-change model turn asks what comes next instead of apologising | `tests/test_order_turn.py` | a439851 | Build 1016 |
| 2026-11-07 | B-90 | Hindi and Telugu log lines no longer fail to print on a Windows console | startup code in `app.py`; the next phone call's log | a439851 | Build 1016 |
| 2026-11-07 | B-89 | Phone barge-in needs 8 frames instead of 4, and the greeting is shorter (unmeasured) | the next quiet phone call (not yet made) | a439851 | Build 1016 |
| 2026-11-07 | B-88 | A call with no order leaves a call record, and the dashboard data carries it | `tests/test_call_stats.py`, `tests/test_lifecycle_fixes.py` | a439851 | Build 1016 |
| 2026-11-07 | B-87 | A long rate limit makes the agent ask the other gpt-oss model instead of failing | `tests/test_llm_groq.py`, five tests | a439851 | Build 1016 |
| 2026-11-05 | B-86 | Every call after the first was deaf (a regression from the B-64 fix, in Build 1013) | `tests/test_lifecycle_fixes.py`; three live calls in a row, 3 of 3 exact | Build 1014 | Build 1014 |
| 2026-11-05 | B-84 | The laptop went to sleep in the middle of an evaluation run and the run ended half done | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-80 | The repository's own hygiene check failed on a committed test file, so GitHub's CI would have been red | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-81 | The spare Timbre connection was thrown away between sentences of a paced run, adding about a second to every reply | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-82 | The model copied earlier changes into later turns, which doubled orders (the main failure of the first valid run) | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-41 | A damaged udhaar ledger was silently replaced with the opening balances | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-42 | Windows file locks made writes fail with PermissionError, and orders could be saved as pending for no reason | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-43 | Removing part of a line could leave a quantity no add would accept | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-44 | A remove with a zero, negative or unreadable quantity deleted the whole line | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-45 | The first B-30 guard swallowed "one more maggi, cash" on a one-line order | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-46 | Ordinary shop talk started the sticky loan mode | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-47 | A new customer named Venkatesh was matched to the customer Venkat | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-48 | An empty cart was told "your order is noted" | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-49 | A tiny loan amount crashed the turn, and a quote of Rs 9 was possible | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-50 | A Timbre spare connection that had gone quiet failed the sentence for 20 to 30 seconds | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-51 | A speech segment with no transcript held the speech recogniser for 8 seconds | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-52 | Any HTTP 400 on a schema request turned the strict schema off for the whole run | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-53 | A rate limit with a long retry-after was retried at once | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-54 | An error in the middle of a streamed reply was invisible | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-55 | An inline comment in .env became part of the key | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-56 | A scripted barge-in never barged in when the gap between turns was longer than the reply | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-57 | Time to first audio was measured from the end of the audio file, not from the caller's last word | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-58 | The "10 dB" noise level was about 7.4 dB by the plain definition | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-59 | Edited script text could play stale cached audio | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-60 | A truncated run was reported as valid | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-61 | The model of a run was recorded as the word "default" | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-62 | On a phone call the caller's words and order were also sent to the phone provider | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-63 | A failed write of the run's result file could abort the remaining calls and still mark the run done | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-64 | A turn still running at hang-up leaked into the next call | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-65 | When speech synthesis failed completely the caller heard nothing but the history said it was said | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-66 | At hang-up the customer was charged before the order file was written | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-67 | One malformed stock.json stopped every call to that shop and the greeting never played | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-68 | A loan turn still in flight after hang-up quoted and showed figures to the next page | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-69 | "Add one kilo sugar again" was treated as a request to repeat the last reply | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-70 | A prefetched knowledge context could be served to another shop or after a price edit | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-71 | A stock edit without a pack size wrote stock.json and then failed, and every later save failed too | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-72 | A call that saved nothing could take the next call's order in the scorer | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-73 | Loan calls inflated the headline rows of the score | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-74 | The English-word error rate counted generic Hindi and Telugu words as right | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-75 | Rate-limit detection missed Gemini, missed a missing log, and counted every refusal twice | see the entry in [bugs.md](bugs.md) (tests named there) | InBul21 | InBul21 |
| 2026-11-05 | B-76 | A truncated auth.json lost every other shop's PIN on the next PIN change | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-77 | Activity-log entries with certain characters disappeared | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-78 | A trailing newline passed the shop-name and call-id checks, and an infinite total broke the dashboards | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-79 | A WebSocket frame that was not a JSON object ended the call | see the entry in [bugs.md](bugs.md) (tests named there) | e8cde76 | Build 1013 |
| 2026-11-05 | B-30 (guarded) | A model note that re-adds every existing line with the same quantity on the turn payment is first chosen is ignored | `tests/test_order_session.py`, 5 tests (replay ignored, real change applied, partial repeat applied, no-payment turn applied, later payment not a replay) | e8cde76 | Build 1013 |
| 2026-11-05 | B-40 | The generated-PIN test compares the PIN with the stored values, not a substring search of a hash file | `tests/test_admin_actions.py`; six reruns green | e8cde76 | Build 1013 |
| 2026-11-03 | B-31 (part) | A spare Timbre connection opened ahead of time; about 0.3 s less per spoken sentence on the real service | `tests/test_tts_gnani.py`, 4 tests; live check: first audio 454–672 ms without, 203–312 ms with | e8cde76 | Build 1013 |
| 2026-11-03 | B-37 | Amounts of a lakh or more are spoken in lakh and crore words (Timbre misreads 6–7 digit numbers in Hindi and Telugu) | `tests/test_loan_flow.py`; live round trip through Prisma | e8cde76 | Build 1013 |
| 2026-11-03 | B-38 | Honorifics removed in Devanagari and Telugu when matching a customer name | `tests/test_credit.py` | e8cde76 | Build 1013 |
| 2026-11-03 | B-35 | The order prompt carries the whole compact catalogue, not a keyword-picked few | `tests/test_order_turn.py`, `tests/test_shop_dukaan_dost.py`; the six failing phrases now right on the live model | e8cde76 | Build 1013 |
| 2026-11-03 | B-36 | The self-echo filter is off for transports that cancel their own echo | `tests/test_order_app.py` | e8cde76 | Build 1013 |
| 2026-11-03 | B-32 | The base transport has a no-op `add_ws_handler`; a test checks every transport method `app.py` calls exists on the replay transport | `tests/test_transport_replay.py` | InBul21 | InBul21 |
| 2026-11-03 | B-29 | The scorer strips the Hindi full stop | `tests/test_score_calls.py` | InBul21 | InBul21 |
| 2026-11-03 | B-28 | Call ids end in milliseconds | `tests/test_order_session.py` | e8cde76 | Build 1013 |
| 2026-11-02 | B-27 | Only a "call ended" reset closes the order | `tests/test_order_app.py`, 3 tests; the first full run scored 0 of 20 before it | e8cde76 | Build 1013 |
| 2026-11-02 | B-26 | Prisma's language is `indic-auto` by default (the service refuses a list) | `tests/test_stt_gnani.py`; five spoken test sentences | e8cde76 | Build 1013 |
| 2026-11-02 | B-19, B-18, B-17 | Indic words kept whole in retrieval; an interrupted reply kept as only what was heard; a price kept with its currency word | tests named in bugs.md | | Build 1004 |
| earlier | B-01 to B-25 | see [bugs.md](bugs.md), "Fixed" | | | Builds 1001 to 1008 |

## Rules for this file
- A fix is logged only with its proof: a test that fails without the fix, or a saved run or live check that shows it. "Looks right" is not a proof.
- Never edit an old line to hide a regression; if a fixed bug comes back, reopen it in [bugs.md](bugs.md) and add a new line here when it is fixed again.
- The build or InBul column is filled in by the change that makes the build.
