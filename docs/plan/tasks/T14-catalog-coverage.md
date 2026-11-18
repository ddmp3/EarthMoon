# T14 Catalogue coverage review

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `data/parameters.yaml`, `docs/wiki/data/`. Branch: `feat/T14-catalog-coverage`.

## Goal
David's request (18/11): now that the needs are clearer, review the Earth, Moon and Mars sources and add every useful, good-quality source, for the widest and most reliable coverage.

## Steps
1. For each kept parameter and each mask, list the sources per body and the coverage holes (T40 measured one: no WorldCover south of 60°S).
2. Add sources that fill a hole or make a kept parameter more reliable. Each fact is read at its source page; unreadable pages stay `not verified` with the reason.
3. Re-check entries that feed a kept parameter and are not verified.
4. Regenerate the wiki tables (`tools/catalog/catalog.py render`), write `docs/wiki/data/coverage-review.md`.
5. Changes to `data/parameters.yaml` are proposed, not applied: David decides.

## Done when
- `python tools/catalog/catalog.py check` and its tests pass; `tools/check.sh` passes.
- The review page lists gaps, additions, entries still blocking a kept parameter, and the proposed parameter changes.
