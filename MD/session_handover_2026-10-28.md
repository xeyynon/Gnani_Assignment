# Session handover: 2026-10-28

## Done this session
| Id | What |
|---|---|
| **Build 1000** (tag `build-1000`) | `git init` on `main`. The baseline commit: the inherited agent, already de-identified (DEC-020). Report: [builds/build-1000.md](builds/build-1000.md) |
| **InBul01** (tag `InBul01`) | Versioning and docs: `scripts/changelog.mjs`, [project_docs_guide.md](project_docs_guide.md), [frontend.md](frontend.md), the root `README.md` (now the Dukaan Dost front page) and `SETUP.md`, `DEC-NNN` ids in [decisions.md](decisions.md), the bug sections in [bugs.md](bugs.md), the `[ ] [/] [x] [~]` marks in [tasks.md](tasks.md), the pipeline agents in [agents.md](agents.md) |

## How versioning works now
- User-visible changes are **builds**: `--pending`, commit, `--tag`, which gives the tag `build-N`, a report and a CHANGELOG entry.
- Everything else is an **InBul**: commit `InBulNN: …`, then `--tag`.
- Full flow: [project_docs_guide.md](project_docs_guide.md). Rules R-8 to R-11 in [rules.md](rules.md).

## Verified
- `--pending` wrote `build-1000.md` and `CHANGELOG.md`; a second run kept the hand-written part and refreshed the file list.
- `--tag` checked that the commit title matches the report, then tagged `build-1000`. It refuses to tag a commit twice.
- No committed file contains the client's name (checked with `git grep --cached`).

## Not done, or blocked
- **Moving the upstream clone out of the folder failed** (permission denied; something may have a file open in it, e.g. VS Code). It's excluded through `.git/info/exclude` meanwhile (DEC-021). Close anything using it, then move the folder to `E:\Projects\upstream-ref\` and delete its line from `.git/info/exclude`.
- **CLAUDE.md is untracked** (also in `.git/info/exclude`) until the client name is out of it (DEC-022).
- Nothing pushed. There's no remote yet.

## Next
1. Rework CLAUDE.md (without the client name), then commit it as an InBul.
2. Build step 1: Gnani and Gemini keys in the example config and key loading, the new requirements, `CALL_DATA_ENABLED=0` by default, B-01. These are user-visible, so batch them into the next build.
3. Build step 2: the smoke test (an InBul), once the Gnani key exists.
