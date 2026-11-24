# Method (v3)

**Question answered.** Where on Earth does the terrain resemble a lunar or Martian environment, compared at the same pixel scale? How sure is that, and what was not compared?

**Not claimed:**
- that a place is an analog: no scenario has a positive validation yet ([VALIDATION.md](VALIDATION.md));
- that a value is a probability;
- that a place is "X% similar".

Detail of each step: [wiki/methods/](wiki/README.md). Decisions: [adr/](adr/README.md). Protocol: [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md).

## Principles
1. **Discovery, not ranking of a list.** Every Earth land cell is assessed. Results never depend on a list of expected sites.
2. **Same pixel on both bodies.** Earth is resampled to the pixel of the planetary product it is compared with (T22):
   - Moon: 40 m (LOLA), 59 m (SLDEM2015);
   - Mars: 115.77 m and 463.08 m (MOLA).
3. **Planetary distributions, not hand-picked intervals.** Each target environment is a distribution of windows computed from planetary data (T20, T41, T48).
4. **Missing data is never a bad value.** Every cell has one of four states: evaluated, partial, hidden, no data. Each state carries its reason.
5. **Similarity, requirements and suitability stay apart.** There is no weighted sum (T23).
6. **Frozen and reproducible.**
   - Each release has an id, a protocol tag, a commit and SHA-256 manifests.
   - Every Earth tile carries its provenance (T52).

## Steps

| Step | What it does | Where |
|---|---|---|
| Profiles | Windows of the target environment on the planetary product: Moon, 8 environments; Mars, 3 phase-1 targets | [methods/profiles.md](wiki/methods/profiles.md), [methods/mars.md](wiki/methods/mars.md) |
| Earth cube | Copernicus DEM resampled to each planetary pixel, metrics per window, 7 WorldCover classes of hidden ground | [runs/earth-cube.md](wiki/runs/earth-cube.md) |
| Comparison | Typicality of each window: two-sided percentile 2 × min(F, 1 − F) in the target distribution (1 = like the median planetary window) | [methods/comparison.md](wiki/methods/comparison.md) |
| Cells | One global equal-area grid of 5 km cells (HEALPix, NSIDE 1303, 25.04 km²); per cell, the median typicality of its windows, coverage and confidence | [methods/sampling.md](wiki/methods/sampling.md) |
| Zones | Connected high-confidence cells with median typicality ≥ τ (0.5; also 0.7 and 0.9), at least 3 cells | [methods/mapping.md](wiki/methods/mapping.md) |
| Validation | Negative and positive controls, masks, self-consistency, reproducibility, Monte Carlo, bias checks, dossiers of the top 20 zones | [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md) |
| Context | Geology (lithology class, crosswalk E17), frozen ground and aridity (models, E18): shown beside slope, never combined with it | [methods/geology-crosswalk.md](wiki/methods/geology-crosswalk.md), [methods/thermal-hydric.md](wiki/methods/thermal-hydric.md) |
| Refresh | Sources watched, impact of a change analysed, no recompute without David's decision | [methods/refresh.md](wiki/methods/refresh.md) |
| Analog links and names | The planet globe beside the Earth map, linked by the same slope percentile (never one planetary place); Earth names from OpenStreetMap, planetary names from the IAU | [methods/analog-links.md](wiki/methods/analog-links.md) |

## What is compared
- **Slope.** The eight terrain metrics carry one independent property, slope, so slope is compared and the rest is shown as context (T21, [methods/parameters.md](wiki/methods/parameters.md)).
- **Confidence of a cell:**
  - **high** with at least 20 valid windows (Moon), or 80% of its windows valid (Mars), and under 10% masked or of unknown cover;
  - **medium** with at least half valid;
  - **low** otherwise.
- **Requirements** (scenarios A and B): met, failed or unknown against documented limits, for example the Apollo LRV climbing limit.
  - They never change a typicality.
  - Lunar limits are never reused on Mars.

## Uncertainty
- **Monte Carlo:** 500 runs, seed 20261119, noise on slope. The Moon uses 0.5°. Mars uses the noise measured from the DEM error: 0.25° at 115 m, 0.04° at 463 m (protocol mars-v2).
- **Reported:** the rank interval of each zone, and its share of runs in the top decile.
- **Not covered:** spatially correlated DEM errors, the boundaries of the conditional environments, and errors of the planetary products beyond their stated uncertainty.

## Scenarios
A permanent lunar base, B robotic lunar exploration, C instruments (no run yet), D Mars: [SCENARIOS.md](SCENARIOS.md). For each one, every release states what was compared, what is not comparable and what cannot be assessed ([LIMITS.md](LIMITS.md)).

## v2
The v2 method scored 37 hand-picked sites with weighted criteria. It is kept for the record in [history/v2-method.md](history/v2-method.md). Its API routes are still served, see the v2 decision in the [release notes](../CHANGELOG.md).
