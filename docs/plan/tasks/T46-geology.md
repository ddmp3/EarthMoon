# T46 Geology and mineralogy dimension

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `data/catalog/*.yaml`, `docs/wiki/methods/parameters.md`, the ADRs, and `docs/SCIENTIFIC_AUDIT.md` section 7 (what can and cannot be compared for regolith). Branch: `feat/T46-geology`.

## Goal
Add ground material to the comparison. It is the largest gap of v1 and v2: the evaluation grid scores criterion 13 (ground material) at 0.

## Context
- **Lunar side:** the south pole is feldspathic highland (anorthosite) [R15]; the maria are basalt.
- **Earth side:** Mistastin is the anorthositic analog named in the v2 docs [R54, R55].
- **Candidate Earth sources** (verified in T12): the GLiM lithology map [R31], national geological maps, EMIT mineralogy (between about 52°N and 52°S) [R35], and ASTER emissivity.
- **Planetary sources:** verified in T10 and T11.

## Steps (TDD)
1. Write a crosswalk between Earth lithology classes and planetary units, with its basis (a reference for each mapping). Mark every uncertain mapping as an expert decision; do not force a class.
2. **Tests:**
   - a known anorthosite body is recognized;
   - known basalt fields are recognized;
   - "unknown lithology" stays missing (never "no match");
   - EMIT absence beyond its coverage is "not covered", not "no mineral".
3. Build the layers. Run the comparison engine and the protocol (with the frozen protocol version).
4. Update `docs/LIMITS.md`: lithology class is not mineralogy; mineralogy is not regolith mechanics.

## Done when
The geology layer is in the API and on the map, the validation outcomes are reported, and checks pass.
