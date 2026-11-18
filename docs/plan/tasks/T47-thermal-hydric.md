# T47 Thermal, ice and hydric dimensions

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `data/catalog/*.yaml`, `docs/wiki/methods/parameters.md` and the ADRs. Branch: `feat/T47-thermal-hydric`.

## Goal
Add the thermal, ground ice and aridity dimensions, compared in the way their physics allows.

## Context
- Absolute temperatures are not comparable: lunar shadowed regions are below 110 K and as cold as 29 K [R1], and the lunar day-night swing is about 300 K [R12]. An Earth match can only be indirect or relative. A within-planet quantile matching was proposed in `tools/analog_backend`: its physical meaning must be justified or the method rejected (T23).
- **v2 issues to avoid:**
  - air temperature taken at the wrong elevation (finding C1, corrected with a lapse rate);
  - the lapse rate applied to minimum temperatures, where inversions dominate (finding L9);
  - one MODIS pixel over one year (finding L5).
- **Candidate sources** (verified in T10 to T12): Diviner, ice stability models, LEND and Lunar Prospector hydrogen; THEMIS thermal inertia and SWIM ice on Mars; MODIS or ASTER land surface temperature, multi-year; permafrost maps; aridity index; ERA5-Land.

## Steps (TDD)
1. For each parameter, state its class (direct, indirect, process, model) and what it does not mean.
2. Tests:
   - inversion-prone valleys are flagged when an elevation correction is used on minimum temperature;
   - multi-year statistics carry an interannual sigma;
   - a modelled value (an ice stability depth, a permafrost probability) is flagged as a model.
3. Build the layers, run the engine and the frozen protocol, and report.

## Done when
The layers are in the API and on the map, the limits are updated, and checks pass.
