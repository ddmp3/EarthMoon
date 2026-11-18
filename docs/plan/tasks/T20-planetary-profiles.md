# T20 Planetary environment profiles (design)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/wiki/data/moon.md`, `docs/wiki/data/mars.md` (outputs of T10 and T11). Branch: `docs/T20-profiles`. Gate G1 must be signed.

## Goal
Define the planetary reference environments that Earth is compared with. Each environment is defined from planetary data, never from Earth sites.

## Context
- v2 has one reference: all 1 km windows of LOLA `LDEM_85S_40M` south of 85°S (`tools/precompute/lunar_reference_v2.py`, `data/reference/moon-south-pole.json`). It mixes shadowed crater floors and walls with lit ridges (open expert decision E8 in `docs/SCIENTIFIC_LIMITATIONS.md`).
- Finding L3: effective resolution differs between bodies and products.

## Steps
1. List the environments with a selection rule built from data.
   - **Moon:** polar highland surfaces (lit); permanently shadowed regions; mare plains; pits and skylights; fresh (Copernican) craters; degraded highland terrain; others if T10 shows data for them.
   - **Mars:** for example volcanic plains, ancient clay-bearing terrain, ice-rich mid-latitude terrain, dune fields, sedimentary basins, cave candidates. Keep only those that T11 shows can be delineated.
   - Each environment is selected by a rule that combines products, for example geologic map unit plus slope mask plus illumination mask.
2. For each environment record:
   - the selection rule and its products (catalogue ids from T10 and T11);
   - the parameters available per dimension, with the scale and the effective resolution of each;
   - the statistics to compute: full distribution (percentiles and joint distribution), not a mean;
   - the known biases and what cannot be characterized.
3. Effective resolution, design an experiment for T41: compare the power spectrum or the variogram of LOLA terrain with Earth DEM terrain. Alternatively, degrade the Earth DEM until the roughness statistics match on flat test areas. Decide the comparison scale per dimension and per environment from that experiment.
4. Write `data/profiles/spec/<body>-<env>.yaml` (spec only; values are computed in T41 and T48) and `docs/wiki/methods/profiles.md` (one section per environment, short).

## Done when
- At least 5 lunar and 4 Martian environments are specified, each with a reproducible selection rule and a list of sources.
- Every environment that was considered and rejected is listed with the reason.
- The south polar v2 reference is reproduced as one of the environments (regression anchor).
- A YAML schema test passes.

## Pitfalls
A profile drawn by hand around a famous place is not reproducible. Use the selection rule.
