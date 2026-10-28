# Guide to the MD files, builds and InBuls

A map of where things are written down in Dukaan Dost and how change tracking works. The scheme matches our other projects.

---

## 1. The MD files
Most live in `MD/`. A few sit at the repo root. `CHANGELOG.md` is generated, never hand-edited.

### Start here
| File | What it is |
|---|---|
| `README.md` (root) | Public front page: what Dukaan Dost is, how to start it |
| `SETUP.md` (root) | Setup and run guide |
| `MD/DukaanDost_MASTER.md` | The master reference: status, document map, one-line architecture |
| `MD/problem_statement.md` | The contest: rules, submission, awards |
| `MD/intent.md`, `MD/prd.md`, `MD/readme.md` | Why we're building it, the product requirements, how this folder works |

### Design and architecture
`architecture.md` (components), `system_design_and_boundary.md` (scope, data flow, trust boundaries), `flow.md` (the runtime, step by step), `agents.md` (the pipeline's threads and models, plus notes for AI coding agents), `integration_handoff.md` (backend interfaces), `deployment.md` (keys, running, settings), `frontend.md` (the order viewer; planned).

### Models
`ml.md` (the models in the stack, choices, the evaluation plan), `ml_model_integration.md` (wiring in Prisma and Timbre), `failmlmodel.md` (models tried and ruled out).

### Registers and logs (the "why" of the project)
| File | What it records |
|---|---|
| `decisions.md` | Every design decision as `DEC-NNN`, with the reasoning |
| `bugs.md` | Every bug: open, fixed uncommitted, fixed (with the build or InBul id) |
| `tasks.md` | Living task tracker with `[ ]`, `[/]`, `[x]`, `[~]` |
| `tried_and_implemented.md`, `tried_and_failed.md` | What worked and what didn't |
| `pain.md` | The shop's pain, and what can break delivery |
| `rules.md` | Working rules, including versioning |

### Plans
`problem_statement-gap-plan.md` (gaps against each award), `poa-non-ml.md` (everything except model work).

### Research and outside input
`external_research.md` (vendor facts with sources), `origin.md` (what we inherit from the upstream project).

### Session handovers
`session_handover_<date>.md`, one per working session.

### Generated
- `CHANGELOG.md`: the build history, regenerated from git by `scripts/changelog.mjs`.
- `MD/builds/build-N.md`: one report per build.

---

## 2. Builds
A **build** is a numbered, user-visible release: anything a caller would hear or the shopkeeper would see (call behaviour, languages, order output, latency the caller notices).

- Numbers start at **1000** and rise by one. Build 1000 is the inherited baseline (DEC-020).
- The number is pinned by a git tag, `build-N`. **The tag is the source of truth.** Never put "(Build N)" in a commit title, and never renumber or move a tag.
- Look one up with `git show build-1003`, or compare two with `git diff build-1000 build-1003`.
- Every build has a report, `MD/builds/build-N.md`:
  - a hand-written part (what changed, why, how it was verified, what to improve next), written once and never overwritten
  - a "Files changed" list, rebuilt from git each time the script runs

### The commit flow
1. `git add` the change files first. The report's file list reads the staged diff.
2. `node scripts/changelog.mjs --pending "<title>" "<one or two plain sentences>" --why "..." --verified "..." --next "..."`
3. `git add MD/builds CHANGELOG.md`, then commit with **the same title** and a real body (what, why, verified).
4. `node scripts/changelog.mjs --tag` pins the number. It doesn't modify files.

### Batching rule
Don't make a build for every small fix. Wait until about **10 fixes** pile up, then make one build of all of them. This applies even to one urgent fix. Push only when explicitly told to ("push"), and push tags too (`git push origin main --tags`; our tags are lightweight, so `--follow-tags` would skip them). Commits carry only Surya's name, with no co-author trailers.

---

## 3. InBuls
An **InBul** is an internal change: docs, MD updates, bookkeeping, tooling, scripts, tests, eval figures, anything a caller or shopkeeper doesn't see.

- Commit titles start with `InBulNN:`, for example `InBul02: Smoke-test script for Prisma and Timbre`.
- Print the next id with `node scripts/changelog.mjs --next-internal`.
- Skip `--pending`. Commit, then run `--tag` to pin an `InBulNN` tag.
- InBul commits get **no build number**, no CHANGELOG entry and no report.
- A merge that brings other work back in is also an InBul. Its work is already counted in the build it came from.

### Build or InBul?
| Change | Label |
|---|---|
| A caller hears it or the shopkeeper sees it: call behaviour, languages, prompts, the stock list, order output, latency | Build |
| Docs, MD updates, scripts, tests, the eval harness and its figures | InBul |
| A new provider (e.g. `stt_gnani.py`) that isn't switched on yet | InBul; switching it on is the build |

---

## 4. How the pieces connect
```
change made
   ├─ user-visible ──> Build N ──> CHANGELOG.md entry + MD/builds/build-N.md + tag build-N
   └─ internal     ──> InBulNN ──> commit + tag InBulNN only

why it was done  ──> decisions.md (DEC-NNN)
bugs found/fixed ──> bugs.md (cites the build or InBul that fixed it)
current state    ──> DukaanDost_MASTER.md and the topic docs (ml.md, flow.md, ...)
```
A build report says **what changed**. `decisions.md` says **why it was designed that way**. `bugs.md` links each fix to the build or InBul that carried it. The master reference and topic docs describe **how things are now**.

## 5. Naming
The project is **Dukaan Dost**. The call pipeline comes from an earlier voice-agent project ([origin.md](origin.md)); the customer it was first built for is never named (R-3). Gnani's models are **Prisma** (STT) and **Timbre** (TTS).
