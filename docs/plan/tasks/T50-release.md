# T50 Documentation, release notes, v2 retirement decision

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, and `CHANGELOG.md`. Branch: `docs/T50-release`. Gate G5 must be signed.

## Goal
The repository describes v3 in a few short pages, the history is complete, and the release is tagged. **Nothing is deployed:** deployment is David's decision after the NASA evaluation.

## Steps
1. Rewrite `readme.md` (80 lines or fewer), `docs/METHOD.md`, `docs/DATA.md`, `docs/SCENARIOS.md`, `docs/VALIDATION.md`, `docs/LIMITS.md` and `docs/ARCHITECTURE.md` for v3. Move superseded pages to `docs/history/` with a one-line note.
2. Check that every number in the docs is produced by a script or a cited run. A link checker and a figure check (a script that greps the numbers quoted in the docs and compares them with run outputs where possible) are part of `tools/check.sh`.
3. Write the release notes in `CHANGELOG.md`; create `git tag v3.0.0` and push the tag to `ddmp3/EarthMoon` only.
4. v2 endpoints: propose keep, deprecate or remove, with usage evidence. David decides.
5. Publish the wiki pages to the GitHub wiki (mirror script from T02).

## Done when
Docs and wiki are consistent, the tag exists, checks pass, and David has the deployment checklist (not executed).
