# Validation (v2, current)

What has been checked, the result, and how to reproduce it. Full protocol and the before/after grid: [wiki/v2/SCIENTIFIC_VALIDATION.md](wiki/v2/SCIENTIFIC_VALIDATION.md). Latest rankings report: [wiki/rankings.md](wiki/rankings.md).

## Results (17 November 2026)

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

## Rank stability labels (interface)

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
