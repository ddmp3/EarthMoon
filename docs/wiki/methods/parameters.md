# Parameters and redundancy (T21)

Catalogue: `data/parameters.yaml` (checked by `tools/profiles/profiles.py`). Measured matrices: [redundancy.md](redundancy.md), from `tools/research/redundancy.py`.

## How redundancy was measured

- **Moon:** all 71,731 windows of 1 km of LOLA LDEM_85S_40M south of 85°S (SHA-256 identical to v2).
- **Earth:** 4,000 points drawn uniformly on the sphere (seed 20261118), one 1 km window of Copernicus GLO-30 at 40 m each. 2,585 fell in the ocean and 5 windows were incomplete; these were counted, not scored. 1,410 windows were kept, 278 of them exactly flat (edited water, ice or salt), so the matrices are also given without those.
- Spearman, Pearson and partial correlations. The rule: a kept pair with |Spearman| > 0.8 on either body needs a written reason. There is none.

## Topography: what the numbers decide

| Parameter | Decision | Why (Spearman) |
|---|---|---|
| `slope_mean` | **keep** | The slope axis |
| `slope_p95`, `slope_max`, `roughness` | drop | 0.87 to 0.99 with `slope_mean` or with each other, on both bodies |
| `roughness_detrended` | context until T41 | **0.18** with slope on the Moon and **0.98** on Earth: it does not measure the same thing on the two bodies |
| `traversable_15`, `traversable_20` | context (operational, scenario B) | Rover requirements, not similarity; VIPER 15° not verified, LRV 20° verified |
| `traversable_25`, `elevation` | drop | 0.89 with `traversable_20` on Earth; datums not comparable |

**Consequence.** At 1 km and 40 m, v2's eight terrain metrics hold **one** independent measured property, slope. v2 robotics counted it three times (finding L1, now confirmed on 71,731 lunar and 1,410 random Earth windows, not only on 37 sites). More terrain information must come from **other scales**, such as slope at 100 m and at 5 km (T22), not from more statistics of the same window.

**The detrended roughness signal.** On Earth, relief left after removing a plane grows with slope; on the Moon, it hardly does. The likeliest cause is that the polar grid is interpolated between laser tracks and so lacks short-wavelength relief (L3). That is a hypothesis, which the T41 effective resolution experiment tests.

## Other dimensions

| Dimension | Kept (compared) | Context only | Dropped |
|---|---|---|---|
| Geology, mineralogy | `lithology_class` (indirect), `mineral_class` (Earth–Mars, interpretation) | `fe_abundance` (selects the mare profile), `silica_emissivity`, `th_abundance` | — |
| Thermal | `lst_amplitude` (model), `thermal_inertia` (model, Mars) | — | `lst_day`, `lst_night`, `t2m_min`: absolute temperatures do not overlap (L5, L9) |
| Hydric and ice | `ground_ice` (classes), `specific_humidity`, `precipitation` (process) | `hydrogen_indicator` (no Earth equivalent) | `relative_humidity` (wrong quantity) |
| Environment | `aerosol_optical_depth` (process, Earth–Mars), `wind_speed` (model, Mars) | — | — |
| Operational | — | `latitude_abs`, `seismic_noise` | `quake_count`, `volcano_distance`, `solar` |

Correlations outside topography are measured in T46 and T47, when those layers are computed.

## What cannot be compared

Gravity; vacuum on the Moon, and a thin CO₂ atmosphere on Mars; radiation and space weathering; absolute temperatures and cryogenic shadow; cold trapping of volatiles; regolith made by impacts without water. These are stated with every result, never scored.
