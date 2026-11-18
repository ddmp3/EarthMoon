# T13 Reference verification

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3. Branch: `docs/T13-references`.

## Goal
Every reference the project relies on is verified at its source or labelled `not verified`. No reference is invented.

## Context
- `docs/SCIENTIFIC_REFERENCES.md` lists R1 to R62. Most DOIs were checked against Crossref on 17 Nov 2026. Still open (finding L8):
  - R9 and R10 (Lunar Sourcebook, a book);
  - R32 (Obu 2019) and R37 (Guth and Geoffroy 2021): the DOI resolves, the title was written from memory;
  - section 8: NASA NTRS 20240013903, 20250004148 and 20250011301 (rover limits: the 15° VIPER limit is the only hard requirement of the mobility scenario), NASA SP-4214, Moriarty and Petro EPSC2022-295.
- T10 to T12 add data set citations: each needs the producer's recommended citation and DOI if one exists.

## Steps
1. Write `tools/research/verify_refs.py` (tested). It reads a list of DOIs and queries the Crossref API sequentially, with a delay of at least 1 s (the API returned 429 when called in parallel). Use a generic User-Agent, never a personal email. Compare authors, title, year, journal and pages.
2. NTRS: open `https://ntrs.nasa.gov/citations/<id>` (web-fetch agent). Record title, authors, year, and the sentence that supports the number we use (for example 15° VIPER).
3. EPSC abstract: check on `meetingorganizer.copernicus.org`. Books: check the publisher or the LPI page.
4. Data set citations from T10 to T12: use the citation the producer recommends.
5. Rewrite the reference list as `docs/REFERENCES.md` (short table: ID, citation, status, verified on, used for). Keep the IDs stable: R1 to R62 keep their numbers.

## Done when
- No `not verified` remains on a reference that supports a number used in scoring, or that number is marked as an expert decision in `docs/SCIENTIFIC_LIMITATIONS.md` (or `docs/LIMITS.md` after T02).
- The script and its tests pass.

## Pitfalls
- Three DOIs recalled from memory were wrong during v2. Never write a DOI from memory.
- A DOI that resolves to a different paper is worse than no DOI.
