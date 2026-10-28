# The MD folder

Project knowledge for Dukaan Dost lives here, one topic per file. Code lives in the repo root. The root [CLAUDE.md](../CLAUDE.md) is the build brief for AI agents, and [DukaanDost_MASTER.md](DukaanDost_MASTER.md) is the index to everything in this folder.

## How to use these files
- **Start at [DukaanDost_MASTER.md](DukaanDost_MASTER.md).** It has the status table and the document map.
- **Update the doc in the same commit as the change.** If a commit changes behaviour, the matching doc changes with it.
- **Versioning:** user-visible changes ship as builds, everything else as InBuls. The full flow is in [project_docs_guide.md](project_docs_guide.md).
- **Record facts and measurements with a date and a source.** Write "measured 2026-11-02, `eval/results.csv`", not "about 1 second".
- **Never write a number you haven't measured.** If it's an estimate, label it as one. The README and the submission may only use measured figures.
- **No client names, real phone numbers or real customer data anywhere** (see [rules.md](rules.md)).

## Which file gets what
| You learned… | Write it in |
|---|---|
| A choice between options, and why | [decisions.md](decisions.md) |
| Something you tried that didn't work | [tried_and_failed.md](tried_and_failed.md) (or [failmlmodel.md](failmlmodel.md) for a model) |
| Something you tried that works and shipped | [tried_and_implemented.md](tried_and_implemented.md) |
| A bug, open or fixed | [bugs.md](bugs.md) (cite the build or InBul that fixed it) |
| What a build changed | Its report in [builds/](builds/), written by `scripts/changelog.mjs --pending` |
| A fact from Gnani's or another vendor's docs | [external_research.md](external_research.md) |
| A task done or added | [tasks.md](tasks.md) |
| End of a working session | A new `session_handover_<date>.md` |

## Naming
File names follow the set used in our other projects, so the layout looks familiar. Two files are named after this project instead: `ps143*.md` became `problem_statement*.md`, and `helpfromexternaalprojectname.md` became [helpfromsmartcaller.md](helpfromsmartcaller.md).
