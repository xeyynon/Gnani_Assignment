# CI/CD

GitHub Actions, in `.github/workflows/`. **None of it has run on GitHub yet** (it needs the first push). What is verified locally is listed at the end.

## CI: every push to `main` and every pull request
`ci.yml`. No secrets or cloud keys are needed; the tests are offline.

| Job | What it checks | Fails when |
|---|---|---|
| Tests (3 runs) | `pip install -r requirements.txt`, then `python -m pytest` on Ubuntu with Python 3.10 and 3.12, and Windows with 3.12 | A test fails, or the pinned requirements no longer install |
| Lint | `ruff check .` for real errors only (syntax errors, undefined names; see `ruff.toml`) | A genuine code error |
| Repo hygiene | `scripts/check_repo.py` and `scripts/check_docs.py` | A key or secret-looking string is committed; a local-only file (`local_config.py`, `.env`, logs, recordings, orders) is tracked; a name from `BANNED_TERMS` appears in a file, file name or commit message; a commit title says "(Build N)"; a relative Markdown link points nowhere |
| Call page | `node --test tests/web/`: the page script parses, its resampler is accurate at 48, 44.1, 32 and 16 kHz, clipping works, the controls exist | The page breaks |
| Container image | Builds the `Dockerfile` (not pushed) and imports the app inside it | The image doesn't build |

`BANNED_TERMS` is an optional **repository variable** (Settings > Secrets and variables > Actions > Variables): a comma-separated list of names that must never be in the repo. It lives in the settings so the names are never committed. The check skips itself, and says so, when it isn't set.

## CD: every build tag
`release.yml` runs when a `build-N` tag is pushed (InBul tags do nothing). It reuses the CI checks as a gate, then:
1. **GitHub Release**: titled "Build N", with the hand-written part of `MD/builds/build-N.md` as the notes (`scripts/release_notes.py`). That includes "how it was verified", so the release says what was *not* tested.
2. **Container image**: built from the tagged commit and pushed to `ghcr.io/<owner>/<repo>:build-N`.

There is deliberately no automatic deployment to a server. The agent is run locally from a browser tab or from the image, and there is no hosted environment yet. Add a deploy job here when there is one.

Workflow files are read from the tagged commit, so the older tags (`build-1000` to `build-1002`) predate them and will not produce releases. The first release will be the next build.

Running the image:
```bash
docker run --rm -p 127.0.0.1:8765:8765 \
  -e GEMINI_API_KEY=... -e GNANI_API_KEY=... -e SARVAM_API_KEY=... \
  ghcr.io/<owner>/<repo>:build-N
```
Then open http://localhost:8765. Publishing on `127.0.0.1` keeps it off your network, and browsers only give the microphone to `localhost` or `https` pages.

## Dependabot
`.github/dependabot.yml` opens weekly pull requests for the pinned Python packages, the GitHub Actions and the base image. CI is the gate.

## One-time setup on GitHub (only you can do these)
1. **Actions** enabled for the repo (Settings > Actions > General).
2. Optional variable `BANNED_TERMS` (above).
3. **Branch protection** on `main` (Settings > Branches): require a pull request and the CI checks above to pass.
4. **Packages**: the first image push creates the package as private. Make it public in the package's settings if you want others to pull it.

## The first push
The GitHub repository was created with one commit (an "Initial commit" containing only a README), so it shares no history with this one. Joining the two without losing either:
```bash
git remote add origin https://github.com/xeyynon/Gnani_Assignment.git
git fetch origin
git merge origin/main --allow-unrelated-histories -s ours -m "InBulNN: Join the GitHub initial commit"
git push -u origin main --tags
```
`-s ours` keeps this repo's files as they are and records the GitHub commit as a parent, so nothing is overwritten and no force push is needed. Use `node scripts/changelog.mjs --next-internal` for the number, and tag the merge commit as an InBul. Push with `--tags`, not `--follow-tags`: our tags are lightweight, and `--follow-tags` only pushes annotated ones.

## Run the same checks locally
```bash
python -m pytest
python -m pip install ruff && ruff check .
python scripts/check_repo.py
python scripts/check_docs.py
node --test tests/web/
BANNED_TERMS="name1,name2" python scripts/check_repo.py     # with the name check
```

## What is verified, and what is not
- **Verified here:** the pinned requirements install in a clean environment on Python 3.12 / Windows and all 124 tests pass; ruff is clean; the Node tests, `check_repo.py`, `check_docs.py` and `release_notes.py` run; the workflow files parse, their jobs are wired correctly and the scripts they call exist; the scripts' tests include bad input, so the checks are shown to fail when they should.
- **Not verified:** nothing has run on GitHub. In particular the Docker image has never been built (no Docker engine here), Python 3.10 and Ubuntu were not tried, and `gh release create`, the image push and the Dependabot config are untested. Expect to fix a red job or two on the first run.
