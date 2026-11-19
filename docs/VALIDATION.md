# Validation

## v3, run-001 (19 November 2026)

The first global discovery run of v3: topography only, scenarios A (lunar base) and B (lunar robotics), protocol `validation-protocol-v2`. Full report: [wiki/runs/run-001.md](wiki/runs/run-001.md).

| Check | Result | Pass |
|---|---|---|
| Positive controls | none exist for A and B: no verified reference names an analog site | no validation |
| Negatives in the top 10% | 0 of 18 for every target (at most 1 allowed) | yes |
| Masks | 17 of 18 negatives masked (a forest-savanna mosaic in the Chaco is 41% hidden) | no |
| Self-consistency (KS ≤ 0.05) | 4 of 5 targets; pits 0.056 on 135 sites | partly |
| Reproducibility | 5 of 5 rebuilt tiles identical | yes |

**What it means:**
- 38 of the 40 best zones are explained artefacts: windows left between hidden ground, or cells cut by the edges of the processing tiles.
- The zone ranking changes a lot with the DEM source (NASADEM: top-20 overlap 40 to 45%) and with the scale (30 m: 35 to 40%). The zone list of run-001 is not a ranking of places.
- One place is plausible: ridges near the MacDonnell Ranges, Northern Territory, Australia. It is small and borderline.
- run-002 will rank zones on high-confidence cells only, and merge the parts of cells cut by tile edges (protocol v3).

**Coverage:** 53% of the assessed cells have most of their ground hidden. The coverage overlay of the interface shows where.

## v2 results (current production)

What has been checked, the result, and how to reproduce it. Full protocol and the before/after grid: [wiki/v2/SCIENTIFIC_VALIDATION.md](wiki/v2/SCIENTIFIC_VALIDATION.md). Latest rankings report: [wiki/rankings.md](wiki/rankings.md).

### Results (17 November 2026)

| Check | v1 | v2 |
|---|---|---|
| Evaluation grid (13 criteria scored 0 to 3) | 15/39 | 28/39 |
| Team expectations met (known analogs in the top half of their modes) | 9/11 | **8/11 (73%, below the 75% threshold)** |
| Negative control (Amazon) excluded in every mode | yes | yes |
| A random ranking does as well | 2.6% | 10.0% |
| TypeScript engine and Python scorer agree on 37 sites × 3 modes | sample data only | exact |

v2 was **not retuned** to meet the expectations. They were written by the team that built v1, so they are a consistency check, not an independent benchmark. Each miss is explained by a measurement:
- Holuhraun is flatter than 95% of the lunar south pole at 1 km;
- Atacama lies on an active subduction margin;
- Svalbard has 106 earthquakes M ≥ 4.5 within 300 km.

**Confidence of the assessments:**

| Mode | Low | Medium | High |
|---|---|---|---|
| Robotics | 17 | 18 | 1 |
| Calibration | 3 | 8 | 25 |
| Colony | 3 | 28 | 5 |

Robotics is the weakest: 1 km terrain statistics change a lot from one kilometre to the next.

**Not covered:** independent expectations (criterion 12) and ground material (criterion 13). Both are open in v3, tasks T25 and T46.

### Rank stability labels (interface)

The share of the ranked list a site moves across between the 10th and 90th percentile of its rank:
- 6% or less: stable;
- up to 25%: moderate;
- more: fragile.

These are presentation choices (`apps/web/src/shared.ts`).

## Reproduce

```bash
tools/check.sh all                                   # every test, audit, Docker e2e and browser audit
python tools/validation/science_grid.py              # counted indicators of the grid
python tools/validation/ablation.py                  # effect of each correction on the rankings
python tools/scoring/score_sites.py                  # v2 rankings (Python reference scorer)
python tools/validation/rankings.py --markdown docs/wiki/rankings.md   # against the running API
```

Quality baseline of the code: [wiki/baseline.md](wiki/baseline.md).
