# Method (v2, current)

Methodology 2.0.0 on data set 2.0.0. Both versions are returned with every API result. Full text, with the reasoning behind each choice: [wiki/v2/SCIENTIFIC_METHODOLOGY.md](wiki/v2/SCIENTIFIC_METHODOLOGY.md). Version 3 (discovery anywhere on Earth) is being designed: [plan](plan/README.md).

**Question answered:** for a stated exploration objective, how far does each of 37 Earth sites fall inside or outside measured lunar ranges and stated requirements, and how sure is that?

**Not claimed:** that any site is equivalent to the Moon, or that a score is a probability.

## Principles

1. Every criterion states its **role**:
   - similarity to a measured lunar distribution;
   - operational requirement;
   - Earth proxy.

   It also states its **basis** (lunar measurement, mission requirement, or expert judgement) and its rationale. All three are served by the API.
2. Similarity intervals come from lunar data, not from hand-picked numbers. Where no measurement exists, the criterion says "expert judgement".
3. A failed hard requirement is never averaged away.
4. A missing value counts neither for nor against a site, and is shown as missing.
5. Score and confidence are separate outputs.
6. Everything is reproducible: frozen data, fixed seed, and an independent Python scorer that gives the API's totals exactly.

## Data

`data/dataset-v2.json`, built offline by `tools/precompute/build_dataset.py`. The SHA-256 of its inputs is stored inside it. Each value is stored as `{value, sigma, sigma_basis, flags}`. Sources and processing: [DATA.md](DATA.md).

| Indicator | What it is | Lunar side |
|---|---|---|
| `slope_mean`, `roughness_detrended`, `traversable_15/20/25`, `slope_p95` | Terrain over a 1 km window on a 40 m grid. Roughness is computed after removing the window's tilt; `traversable_15` is the share of the window at 15° or less | Same code on LOLA `LDEM_85S_40M`, 71,731 windows south of 85°S |
| `t2m_mean`, `t2m_min` | NASA POWER air temperature, corrected to the site elevation (6.5 K/km); sigma includes the correction | None (proxy) |
| `wind`, `specific_humidity`, `precipitation` | NASA POWER cell values; set to missing if the cell is more than 1 km above or below the site | None (proxy) |
| `quake_m45_count` | USGS earthquakes M ≥ 4.5 within 300 km, 2000 to 2026-11-01, Poisson sigma | None (proxy) |
| `lst_amplitude`, `ndvi` | MODIS, 2024, one pixel. NDVI is a vegetation filter, not a criterion | None |
| `lava_tube_evidence` | 3 demonstrated, 2 probable (each with a reference), 1 predisposition only; empty = not assessed | Not used by the preset modes |

Deprecated, still served, used by no preset mode: `volcano_distance`, `quake_count`, `humidity`, `roughness`, `slope_max`, `solar`. The reasons are in [wiki/v2/SCIENTIFIC_AUDIT.md](wiki/v2/SCIENTIFIC_AUDIT.md).

## Scenarios

Defined in `apps/api/src/scoring/modes.ts` and mirrored in `data/reference/scenarios-v2.json`.

- **Robotics:**
  - `slope_mean` and `roughness_detrended` inside the lunar interquartile range;
  - at least half of the ground under 15° (hard requirement);
  - dry ground.
- **Calibration:** one weight per instrument (drill, wind, gas, seismometer, thermal). Every criterion rests on judgement.
- **Colony:** cold, high latitude, slope of 5° or less (hard requirement), few earthquakes. Every criterion rests on judgement.

## Scoring

For a criterion with interval `[min, max]`, the score is:
- 1 inside the interval;
- falling linearly to 0 at `tolBelow` below and `tolAbove` above. For similarity criteria, these reach the lunar 5th and 95th percentiles.

For a site, over the criteria `K` that have a value, among all criteria `A`:

```
total    = 100 · Σ_K w·s / Σ_K w           coverage = Σ_K w / Σ_A w
totalMin = 100 · Σ_K w·s / Σ_A w           totalMax = 100 · (Σ_K w·s + Σ_{A\K} w) / Σ_A w
```

The total is then multiplied by a vegetation factor: 1 up to NDVI 0.2, falling to 0 at 0.6, where the site is excluded.

Ranking order:
1. sites that meet their requirements;
2. sites that fail a requirement, with their total kept;
3. sites excluded for vegetation.

## Uncertainty and confidence

A Monte Carlo of 500 runs (seed 20261115) perturbs:
- weights by ±50%, tolerances by ±25%, bounds by ±10%;
- every value with a sigma, redrawn from a normal distribution and clipped to its physical range.

Per site, it gives the rank and total P10 to P90, the share of runs in the top half, and the share of runs that meet the requirements.

Confidence label (presentation choices):
- **low:** coverage below 0.6, or an unknown requirement, or a total interval wider than 30 points;
- **high:** coverage of 0.9 or more and an interval of 15 points or less;
- **medium:** otherwise.

`GET /api/sites/{id}` adds an explanation: strengths, weaknesses, decisive criteria, missing values, flagged values, and the share of the result that rests on judgement.

What the uncertainty does not include: values without a sigma (wind, humidity, precipitation, MODIS), correlated errors, the choice of criteria, the 40 m scale. Limits: [LIMITS.md](LIMITS.md).

## v3 comparison engine (T42, not served yet)

Code: `tools/discovery/compare.py` and `compare_run.py`. Every v3 number is computed once, in Python (ADR-005). The v2 engine above is unchanged.

- **Scale:** Earth is measured at the pixel scale of the lunar product it is compared with: 40 m against LOLA polar targets, 59.2 m against SLDEM2015 targets. Lunar targets without an Earth equivalent (5 m windows) are reported as not comparable.
- **Similarity:**
  - per parameter and target: the two-sided percentile typicality of each 1 km window against the lunar windows (T23);
  - per 5 km cell: the median, the quartiles and the share of windows above 0.5, never one number alone;
  - checked on held-out lunar blocks: mean 0.500, Kolmogorov–Smirnov distance 0.005 to uniform.
- **Hidden ground:** a window with at least half forest, buildings, water, snow or ice (WorldCover) is not compared; it is counted as masked. Without WorldCover data the cover is unknown, never assumed bare.
- **Requirements:**
  - each is `met`, `failed` or `unknown` per window; a cell meets it when at least half of its windows with data do;
  - a failed eliminating requirement marks the cell as eliminated, and its similarity stays visible;
  - no output is averaged with another.
- **Operational suitability:** its own value (scenario A: base slope, 1 at 5° or less, 0 at 10°; scenario B: share of the window at or below 20°).
- **Coverage and confidence:**
  - coverage counts windows, valid windows, masked windows and windows of unknown cover;
  - confidence is high with at least 20 valid windows and under 10% masked or unknown, medium with at least 10, low otherwise.
- **Uncertainty:** 500 Monte Carlo runs (seed 20261119, slope noise 0.5°) give each cell a rank interval and the share of runs in the top decile.
- **Earth smoothing** (David, 18/11/2026): none by default; the ranking with a 1-pixel smoothing is reported as a sensitivity run.
