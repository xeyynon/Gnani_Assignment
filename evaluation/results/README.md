# Saved results

Every number in the README, the videos and the posts must come from a file here (rule R-5), and only from a run that is **valid**.

A file whose name starts with **INVALID_** or **INCOMPLETE_** is kept as evidence, not as a result:
- `INVALID_`: the language model refused some requests (its rate or daily limit), so some turns were answered with the apology instead of the model's note.
- `INCOMPLETE_`: the run stopped before every scripted call finished (a timeout, the agent exiting, or the machine going to sleep).

Do not quote the figures in those files. What they showed is written up in `MD/bugs.md` (B-33, B-34, B-81, B-84, B-85); the search-mode run of 2026-11-06 is listed in the hand-over note.

Older files (before 2026-11-05) were scored with an earlier scorer: their time to first audio is measured from the end of the audio file and their noise level used a different definition. They say so in their own header.

**Stock change, 2026-11-07 (B-92):** the demo shop now sells atta loose by the kilo (`ATTA-1KG`) as well as in 5 and 10 kg bags, and the scripts expect it. Results saved before that date were scored against the old list (atta only as a 5 kg bag) and are not comparable with later runs; `credit_loans_clean_120b` is one of them.

**stt_accuracy_prisma (2026-11-07):** Prisma alone, no language model: all 65 turns of `orders.json` sent four ways (clean or a simulated phone line, language chosen or named). Synthetic voices and my own phone-line simulation, not Exotel's audio; "exactly right" counts only turns whose words match the script word for word (after number words are turned into digits), so Hinglish turns written in Latin letters can never match the Devanagari Prisma writes. Run with `python evaluation/stt_accuracy.py --out evaluation/results/stt_accuracy_prisma`.
