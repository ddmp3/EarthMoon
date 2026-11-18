# T02 Docs reset: short README, wiki, history

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3. Branch: `docs/T02-docs-reset`.

## Goal
A documentation set a human reads in minutes. History is kept, not deleted.

## Context
- Today `docs/` holds v1 pages (`scenarios.md`, `validation.md`, `sources.md`, `architecture.md`), six v2 pages (`SCIENTIFIC_*.md`, about 100 KB in total), the Montréal presentation PDF (v1 claims: "75% expectations met", volcano distance as basalt, "Svalbard air is humid", all contradicted by v2), and `screenshots/`.
- `readme.md` starts with a French notice written by David (this repository is the v2 clone; the original is under NASA evaluation and must not be modified). Keep that notice, in David's words.
- Detailed pages go to `docs/wiki/` (versioned with the code). The GitHub wiki is enabled and is a **mirror** of `docs/wiki/`.
- Decision 6.4: "human readable; nobody will write 50k pages; be concise".

## Steps
1. Target layout:
   ```
   readme.md          what, why, how to run, links (≤ 80 lines)
   CHANGELOG.md       one entry per merged task
   docs/
     METHOD.md        current method in 2 to 3 pages (v2 now; v3 rewritten in T50)
     DATA.md          sources used, one table
     VALIDATION.md    current results and how to reproduce
     LIMITS.md        what results do not mean; expert decisions
     ARCHITECTURE.md  components, data flow, how to run checks
     plan/            this plan
     wiki/            long material: inventories, experiments, runs, history
     history/         Montréal deck and v1 pages, each with a one-line "historical, superseded by …" note
   ```
2. Condense the `SCIENTIFIC_*.md` files into the short pages. Move the full originals to `docs/wiki/v2/` without changing them, so nothing is lost.
3. Fix every internal link (`grep -rn "\.md" docs readme.md`), including links from code comments and from `apps/api/openapi.yaml`.
4. `CHANGELOG.md`: add retroactive entries for v1 (hackathon, 15 Nov 2026) and v2 (PR #1, 17 Nov 2026), then this task.
5. Remove from the README the claims that are no longer true.
6. Write `tools/publish_wiki.sh`, which copies `docs/wiki/**/*.md` to the wiki repository `https://github.com/ddmp3/EarthMoon.wiki.git`:
   - flatten paths into page names (`data/moon.md` becomes `data-moon.md`);
   - rewrite relative links;
   - generate `Home.md` and `_Sidebar.md`;
   - commit with the source commit hash in the message.
   GitHub creates the wiki repository only after a first page exists. If the clone fails, ask David to create a "Home" page once in the web interface. Run `gh` through WSL. Test the link rewriting with a small fixture.

## Done when
- The README is 80 lines or fewer and every link resolves (check with a script).
- No figure in `docs/` (outside `history/` and `wiki/v2/`) contradicts `docs/wiki/v2/SCIENTIFIC_VALIDATION.md`.
- `tools/check.sh all` passes.

## Pitfalls
- Do not rewrite the method itself here: v3 rewrites it in T50. This task only shortens and restructures.
