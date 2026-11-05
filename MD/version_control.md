# Version control: how it works in this project

How changes are numbered, recorded, committed and pushed. This is the one page to read before making a commit. The same scheme is used in Surya's other projects, so the reference Surya supplied at the start (the "builds vs InBuls" guide) is kept here, in full, in section 11. The shorter rules are in [rules.md](rules.md) (R-8 to R-11) and the file map in [project_docs_guide.md](project_docs_guide.md).

## 1. The idea in one minute
Every change is one of two kinds:

| Kind | What it is | Label | Number |
|---|---|---|---|
| **Build** | Something a **caller hears** or a **shopkeeper sees**: how a call goes, languages, prompts, the stock list, order output, the pages, latency the caller notices | `build-N` | 1000, 1001, 1002, ... |
| **InBul** (internal build) | Everything else: docs, notes, scripts, tests, the evaluation harness and its figures, tooling | `InBulNN` | 01, 02, 03, ... |

A number is **pinned by a git tag** with that name. The tag is the source of truth; the commit title never carries the number. Builds are **batched**, about ten fixes to a build, so the build list stays short and meaningful.

```
change made
   ├─ a user would notice it ──> Build N ──> commit + MD/builds/build-N.md + CHANGELOG.md entry + tag build-N
   └─ internal               ──> InBulNN ──> commit titled "InBulNN: ..." + tag InBulNN (no report, no changelog entry)
```

## 2. Why two kinds
- A **build** answers "what did the product do differently from this point?" You can show a build to someone who only uses the product.
- An **InBul** keeps the history honest about the work that is not product: research, plans, tests, the evaluation. Without it, either the build list fills with noise or that work goes unrecorded.
- **Batching** stops one-line fixes from each becoming a "release". It also applies to a single urgent fix: wait and ship it with the next batch (unless Surya says otherwise).

## 3. Is it a build or an InBul?
| Change | Label |
|---|---|
| A caller hears it or the shopkeeper sees it: call behaviour, languages, prompts, the stock list, order output, the call page, the dashboards, latency | **Build** |
| Docs, `MD/` updates, scripts, tests, the evaluation harness and its figures | **InBul** |
| A new provider that is **not switched on yet** (for example `stt_gnani.py` before `STT_PROVIDER=gnani` is the setting) | **InBul**. Switching it on is the build |
| A merge that brings other work back in | **InBul**. The work is already counted in the build it came from |
| A bug fix a caller would notice | **Build** (batched with the next ones) |
| A bug fix nobody would notice (a test, a log line) | **InBul** |

When in doubt: would Surya mention it to a user? Build. If not: InBul.

## 4. Numbers and names
- **Builds** start at **1000**. Build 1000 is the inherited baseline (the voice agent this project started from, with the earlier customer's identity removed, DEC-020). Each build is the next whole number. Tag: `build-1004`.
- **InBuls** start at `InBul01`, two digits, and rise by one. Tag: `InBul14`. Print the next free id with `node scripts/changelog.mjs --next-internal`.
- **Never** put "(Build N)" in a commit title. The tag carries the number. `scripts/check_repo.py` fails the check if a title has it (R-9).
- **Never renumber or move a tag.** `--tag` refuses to tag a commit twice.
- **Tags are lightweight** (not annotated). That matters for pushing, section 8.

## 5. The files involved
| File | What it is | Who writes it |
|---|---|---|
| `MD/builds/build-N.md` | One report per build: what changed, why, how it was verified, what to improve next, and the list of changed files | The first four parts by hand, **once**; the file list is rebuilt by the script |
| `CHANGELOG.md` | The build history, newest first | **Generated** by `scripts/changelog.mjs`. Never edit by hand (R-11) |
| `scripts/changelog.mjs` | The tool that does the bookkeeping | Code |
| `MD/decisions.md` | Why a change was designed the way it was (`DEC-NNN`) | By hand |
| `MD/bugs.md` | Every bug, and which build or InBul fixed it | By hand |
| `MD/tasks.md`, `MD/DukaanDost_MASTER.md`, the handover notes | Current state | By hand |

A build report says **what changed**. `decisions.md` says **why**. `bugs.md` links each fix to the build or InBul that carried it. The master and topic docs say **how things are now**.

## 6. Making a build, step by step
1. Make the change. Run the checks (section 9).
2. `git add` the files of the change **first**. The report's file list reads the staged diff.
3. Write the report and the changelog entry:
   ```
   node scripts/changelog.mjs --pending "<title>" "<one or two plain sentences on what changed>" \
       --why "<why>" --verified "<how it was checked, honestly>" --next "<what to improve next>"
   ```
   This writes `MD/builds/build-N.md` for the next number and regenerates `CHANGELOG.md`. If the report already exists, its hand-written part is kept.
4. `git add MD/builds CHANGELOG.md`.
5. `git commit` with **the same title** as in step 3, and a real body: what, why, verified. No attribution or co-author lines.
6. `node scripts/changelog.mjs --tag` pins `build-N` on that commit. It checks that the commit title matches the report, and it does not modify files.
7. **If the build changes how a page looks**, record it on screen too: `python scripts/ui_check/snapshot_release.py build-N <NN>-build-N`, add an entry for that folder in `snapshots/history/changes.json`, run `python scripts/ui_check/history_index.py`, and commit `snapshots/` as an InBul. [`snapshots/CHANGES.md`](../snapshots/CHANGES.md) is the release-by-release picture of the UI (how it works: `MD/frontend.md`, "The history of the UI").

Title style: plain words, what the product now does (for example "The order flow: the model reads the order and the code does the money"). No "feat:" prefixes, no number.

## 7. Making an InBul, step by step
1. `node scripts/changelog.mjs --next-internal` prints the id, for example `InBul18`.
2. `git add` the files.
3. `git commit` with a title that starts with the id: `InBul18: Short description`. Add a short body.
4. `node scripts/changelog.mjs --tag` pins `InBul18`.

An InBul has **no report and no changelog entry**. If you do both a build and an InBul in one sitting, they are two separate commits.

## 8. Pushing
- **Commit and push only when Surya asks.** Never on our own.
- Push **branch and tags together**: `git push origin main --tags`. Tags are lightweight, so `--follow-tags` would skip them (an earlier note said otherwise; it was wrong and was corrected).
- The remote is `https://github.com/xeyynon/Gnani_Assignment`, branch `main`, no force pushes. The remote's first commit has a placeholder title ("InBulNN: Join the GitHub initial commit"); it is cosmetic and is left alone, because changing it would need a force push.
- Commits carry **only Surya's name**: no co-author trailers, no "generated by" lines.
- Look up any build later: `git show build-1004`, `git diff build-1000 build-1004`, `git log --oneline`.

## 9. Checks before every commit
Run all of these. They are also what GitHub's CI runs on every push (`.github/workflows/ci.yml`).
```
python -m pytest                       # all Python tests
node --test tests/web/                 # the pages' tests
python scripts/check_repo.py           # no secrets, no local-only files, no "(Build N)" titles, no banned names
python scripts/check_docs.py           # every relative link in the Markdown resolves
```
What `check_repo.py` refuses: a tracked `.env`, `local_config.py`, logs, recorded calls, `data/`, or `orders/` (except `orders/samples/`); anything shaped like an API key or private key; a commit title with "(Build N)"; and, if the `BANNED_TERMS` setting exists (kept **outside** the repo), any listed name in a file, a file name or a commit message.

Also by hand, before a push: **the earlier customer's name must appear nowhere** in tracked files or commit messages (R-3). The name is not written in this repo, not even here; it is kept in the local `.git/info/exclude` file and the `BANNED_TERMS` CI setting.

## 8a. What must never be committed
Keys and passwords (`.env`, `local_config.py` stay gitignored); real phone numbers, IDs, addresses or recorded calls (all data is synthetic); anything from the earlier customer; generated audio (`evaluation/audio/` is ignored). Saved evaluation **results** in `evaluation/results/` **are** committed, because the README may quote only numbers that come from them (R-5).

## 10. How releases and CI fit in
- `ci.yml` runs the checks above on every push and pull request.
- `release.yml` runs when a `build-*` tag is pushed: it publishes a GitHub Release whose notes come from the build report, and builds a container image.
- Dependabot proposes dependency updates.
- CI has to be watched: it is read on GitHub (the Actions tab), not from this machine.

## 11. The reference Surya supplied (kept in full)
This is the guide Surya pasted at the start of the project, from their other project. It is the origin of everything above; where this project differs, section 12 says how.

> **Versioning: builds vs InBuls.**
> Two kinds of change. A **build** is a numbered, user-visible release (call behaviour, languages, order output, latency the caller notices). An **InBul** is an internal change (docs, MD updates, bookkeeping, tooling, scripts, tests, eval figures).
> - Build numbers start at 1000 and rise by one; Build 1000 is the baseline. The number is pinned by the git tag `build-N`, which is the source of truth. Never put "(Build N)" in a commit title. Never renumber or move a tag.
> - Each build has a report `MD/builds/build-N.md` (hand-written part once, "Files changed" rebuilt from git) and an entry in the generated `CHANGELOG.md`.
> - Commit flow: `git add` the change files; `node scripts/changelog.mjs --pending "<title>" "<summary>" --why ... --verified ... --next ...`; `git add MD/builds CHANGELOG.md`; commit with the same title; `node scripts/changelog.mjs --tag`.
> - Don't make a build for every small fix. Wait until about 10 fixes pile up, then make one build of all of them. This applies to a single urgent fix too.
> - InBul commits are titled `InBulNN: ...` (next id from `--next-internal`), get no build number, no changelog entry, no report; commit, then `--tag`.
> - Build or InBul? User-visible = build. Docs, scripts, tests, eval figures = InBul. A new provider not yet switched on = InBul; switching it on = build.
> - Push only when told to, with tags: `git push origin main --tags`. Commits carry only the owner's name.
> - The generated `CHANGELOG.md` is never edited by hand. A merge that brings other work back in is an InBul.

The same material, organised for this project, is in [project_docs_guide.md](project_docs_guide.md) sections 2 to 4.

## 12. What is specific to this project
- **Branches (2026-11-06): three, no more by default.** `main` is what is finished and merged. `ui-ux-upgrade` is the one branch for every change to how the pages look or work for a person (the call page, the shop dashboard, the admin page, the sign-in page, the palette, the snapshots of them), and it is merged into `main` through a pull request when a build is ready. `backend-fixes-and-evaluation` is the same for the agent, the evaluation and the docs behind them. A fourth branch is made only for something that must not travel with either, such as an experiment that may be thrown away or a change that is risky enough to want its own review; delete it when it is merged. A merged branch is deleted straight away (git keeps its commits in `main`), so the list stays short. Earlier one-off branches (`admin-dashboard`, `admin-dark-ui`, `call-loan-panel`, `frontend-audit`, `agent-work`) were merged and removed.
- **The two sessions share one folder, so they share one checked-out branch.** Switching branch changes the files under the other session. Until each has its own folder (`git worktree add ../Gnani-ui ui-ux-upgrade`), switch only when the other session is idle, and stage by file name, never `git add -A`.
- **Two sessions work at once** (2026-11-02 onward): one on the pages and their look and feel, one on everything behind them. Each commits only its own files, and each takes the next free number when it commits. If two changes touch the same file, one waits.
- **Next free id means: look at the tags again just before committing.** Another session may have taken `build-1010` or `InBul18` since you last looked. `--next-internal` and `--pending` read the current tags, so use them and do not guess the number.
- **Bug and decision numbers** (`B-NN`, `DEC-NNN`) have the same problem: check the end of the file before using the next one. This happened on 2026-11-03, when two bugs were given the same id and one was renumbered.
- **The first commits** were made before the scheme was set up: the history starts with a placeholder commit, then `build-1000` (the inherited baseline), then `InBul01` (the docs and the changelog script).
- **Everything else** — record every decision, every bug, every measured figure — follows the registers in section 5.

## 13. The history so far
| Tag | Date | Title |
|---|---|---|
| build-1000 | 2026-10-28 | Baseline: the inherited voice agent, de-identified |
| InBul01 | 10-28 | MD docs and build/InBul versioning |
| build-1001 | 10-28 | Gnani and Gemini keys, Gemini by API key, call recording off by default |
| InBul02 | 10-28 | Research: Prisma v3.0, Timbre normalisation, contest and Gemini limits |
| InBul03 | 10-28 | Idea research: competing entries and options |
| InBul04 | 10-28 | Decide on kirana orders plus an udhaar ledger |
| InBul05 | 10-28 | Problem research: SIH 2026 and other voice problem statements |
| InBul06 | 10-28 | Decide on shop orders plus Udyami loan guidance |
| InBul07 | 10-28 | Loan calculator for Udyami guidance |
| InBul08 | 10-28 | Plan for running without the Raspberry Pi |
| InBul09 | 10-28 | Audio transport interface; Pipewire code moved behind it |
| InBul10 | 10-28 | Rename and restructure the repo for Dukaan Dost |
| InBul11 | 10-28 | Profile the per-frame audio cost; record the Python-first, Cython-later plan |
| build-1002 | 10-28 | Run as software only: call from a browser, Raspberry Pi support removed |
| InBul12 | 10-28 | CI/CD with GitHub Actions |
| build-1003 | 10-28 | Shopkeeper dashboard, and one agent for many shops |
| InBul13 | 10-28 | Keyless dashboard preview |
| build-1004 | 11-02 | Gnani speech backends, the demo shop, and fixes found by the research |
| InBul14 | 11-02 | Research papers, pipeline expectations, and the records for the Gnani work |
| InBul15 | 11-02 | Smoke runs after the Prisma wait fix |
| build-1005 | 11-02 | Call page and dashboard redesign, with a live transcript |
| build-1006 | 11-02 | One shared colour palette for the call page and the dashboard |
| build-1007 | 11-02 | Pages built from components, with a bento and glass design |
| build-1008 | 11-02 | The order flow: the model reads the order and the code does the money |
| InBul16 | 11-02 | Records for the order flow, the Groq model choice and the first real-service runs |
| InBul17 | 11-02 | Status page, bug list, task list and hand-over brought up to date |
| build-1009 | 11-03 | The admin dashboard: look after every shop from one page |

Newest first, with the full list of files per build, is in [../CHANGELOG.md](../CHANGELOG.md). This table was copied from `git tag` on 2026-11-03 and will go stale: the tags are the truth.

## 14. Quick card
```
build:   git add <files> -> changelog.mjs --pending "title" "summary" --why .. --verified .. --next ..
         -> git add MD/builds CHANGELOG.md -> git commit (same title) -> changelog.mjs --tag
inbul:   changelog.mjs --next-internal -> git add -> git commit "InBulNN: title" -> changelog.mjs --tag
push:    git push origin main --tags        (only when Surya says so)
never:   "(Build N)" in a title - hand-editing CHANGELOG.md - moving a tag - keys - the earlier customer's name
```
