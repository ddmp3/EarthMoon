# T24 Scenarios v3 (design)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/methods/profiles.md`, `docs/wiki/methods/parameters.md`, and `docs/SCIENTIFIC_LIMITATIONS.md` section 3 (expert decisions E1 to E12). Branch: `docs/T24-scenarios`.

## Goal
Each scenario states its target planetary environment(s), the dimensions compared for similarity, its operational requirements (each with a cited source), its eliminating constraints, and its evaluation method. Mars is designed on its own terms.

## Context
- v2 scenarios (`apps/api/src/scoring/modes.ts`, mirrored in `data/reference/scenarios-v2.json`): robotics, calibration, colony. Calibration and colony have no criterion based on a lunar measurement (finding L4).
- Scenarios requested by David:
  - **A. Permanent lunar base:** slope and buildability, terrain stability and morphology, geology and materials, resources, thermal conditions, illumination, constraints of permanently shadowed regions, natural shelters, mass-wasting risk, mobility and construction.
  - **B. Robotic lunar exploration:** slope, roughness at several scales, obstacles, traversability, terrain stability, regolith, thermal constraints, crater and relief hazards, access to science targets.
  - **C. Instrument calibration and validation:** geology instruments, navigation systems, thermal sensors, radar, mineralogy analysers, sampling systems, mobility systems.
  - **D. Mars exploration and settlement:** geology and mineralogy, sediments, volcanic terrain, ancient aqueous environments, aeolian processes, dust, temperature, water and ice, subsurface, mobility and human exploration.

## Steps
1. For each scenario (and each instrument of C), write:
   - the objective;
   - the target environments (ids from T20);
   - the similarity dimensions and parameters (ids from T21);
   - the operational requirements, each with a verified source (T13) or marked as an expert decision;
   - the eliminating constraints;
   - what the scenario cannot assess.
2. Mark every property that Earth data cannot measure. Do not replace it silently with a proxy; if a proxy is used, name it as a proxy.
3. Carry over the open expert decisions E1 to E12 that still apply, and add the new ones.
4. Write the outputs:
   - `docs/SCENARIOS.md` (short, one table per scenario);
   - `data/scenarios/*.yaml` (machine-readable, validated by a schema test). These replace `scenarios-v2.json` in T42.

## Done when
- All four scenarios and every instrument of C are specified.
- No requirement number lacks a source or the expert-decision label.
- David can read the whole of `docs/SCENARIOS.md` in 10 minutes.

## Pitfalls
"Cold, polar, flat, quiet" was the v2 colony scenario (finding K2): a list of comfortable field-station conditions is not an analog.
