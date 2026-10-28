# Session handover: 2026-10-26

## Done this session
1. Read the build brief ([CLAUDE.md](../CLAUDE.md)).
2. Cloned the upstream GitHub repo (latest commit `a69a3bf`, 2026-08-19) to compare it with this folder. **It's currently at the project root.** Its folder name, git remote, history and `shops/` contain the client's name, so it **has to move outside `E:\Projects\Gnani` before `git init`** (R-3).
3. Diffed every shared file, ignoring line endings. **This folder is already the latest upstream code, de-identified.** No code port is needed. See [origin.md](origin.md).
4. Created the `MD/` folder: 26 files, with the upstream HANDOFF lessons carried over without client names.

## Found along the way
- **B-01:** the startup check misses the placeholder in `local_config.example.py`.
- **B-02:** `LLM_HISTORY = 3` and `LLM_TOKENS = 100` will lose items in long orders. A design issue for step 8.
- **B-03:** call recording is on by default. It has to be off (DEC-007).
- CLAUDE.md says "five threads"; there are six (`vad_metrics_writer` was added upstream on Aug 17).

## Not done (nothing in the code has changed)
- No `git init` yet.
- No Gnani key yet (Surya to register).

## Next
1. Move the upstream clone out of the project folder.
2. Update CLAUDE.md where these docs found it out of date (thread count, the "port" question settled, links to `MD/`).
3. Build step 1 (setup), then step 2 (smoke test) once the Gnani key exists.
4. Decide DEC-005 (language selection) after the smoke test.
