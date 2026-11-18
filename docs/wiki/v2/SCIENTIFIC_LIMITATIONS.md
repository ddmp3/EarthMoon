# Limits, uncertainties and points needing human expertise

What EarthMoon v2 cannot conclude, how uncertain its numbers are, and which decisions must be taken by domain experts rather than by the tool or its developers. References `[Rn]` are in [SCIENTIFIC_REFERENCES.md](../../REFERENCES.md).

## 1. What a result means and does not mean

A v2 result says: *for this scenario, measured on these data, this site falls inside or outside the lunar ranges and the stated requirements by this much, with this confidence.* It does not say:

- that the site is equivalent to the Moon, or a given percentage similar to it;
- that the site is a validated test site: no score replaces a field campaign and a review by the team that will run the test;
- anything about the ground material: v2 compares terrain shape and climate proxies; lithology, mineralogy, grain size, regolith mechanics and dust are not measured (audit, section 7);
- anything below the 40 m DEM baseline: rocks, small craters, the slope under a wheel;
- that a site without a lava tube level has no cave: it was not assessed;
- that a low earthquake count means low seismic noise at the site;
- that a high latitude reproduces lunar polar illumination.

What Earth cannot reproduce at all: lunar gravity (one sixth), vacuum, absence of weather, the radiation environment [R46], the cold of permanently shadowed regions (below 110 K [R1]), the electrostatic behaviour of dust in vacuum [R11].

## 2. Uncertainties

| Source of uncertainty | How v2 handles it | What is still missing |
|---|---|---|
| Position of the site point (one km more or less) | Spread of the 3 x 3 neighbouring windows, propagated by Monte Carlo | Sites are points; several coordinates are approximate (`data/candidates.json`) |
| DEM errors | Not modelled separately; partly inside the neighbourhood spread | Copernicus DEM vertical error, LOLA interpolation between tracks |
| Resolution difference between sources | Earth and Moon terrain on the same 40 m grid | Climate at 50 km, MODIS at 500 m to 1 km, terrain at 40 m: mixed scales |
| Reanalysis temperature | Lapse-rate correction with sigma = sqrt(1.5² + (2 K/km x Δz)²) | The 1.5 K reanalysis error is an assumption; inversions in polar valleys are not modelled |
| Wind, humidity, precipitation, MODIS | Flags only | No sigma: intervals are lower bounds |
| Earthquake counts | Poisson error | Choice of radius and period not varied |
| Classification errors (lava tube levels) | Levels 2 and 3 only with a reference | Level 1 rule (30 km, rock list) is a choice |
| Expert choices (weights, tolerances, bounds) | Monte Carlo ±50%, ±25%, ±10% | The choice of criteria itself is not varied |
| Model uncertainty | Not quantified | Linear scoring and weighted mean are conventions [R51] |
| Representativeness of Earth data for the Moon | Stated per criterion (`role`, `rationale`) | Not quantifiable with the current data |
| Extrapolation from Earth to lunar conditions | Not quantified | Requires physical models (gravity, vacuum) outside the scope of the tool |

Correlated errors are ignored: values are redrawn independently. This probably understates the uncertainty of sites whose climate values all come from the same mis-placed cell.

## 3. Decisions that need human expertise

The developer of v2 did not decide these points, or decided them provisionally and labelled them `expert_judgement`. Each needs a named expert or a documented requirement before it can be called justified.

| # | Decision | Current provisional choice | Who should decide | Why it matters |
|---|---|---|---|---|
| E1 | Climbing limit and required traversable share for the mobility scenario | 15° (VIPER, from NASA NTRS reports cited by the team in v1, not re-verified), half the window at or below it, failure below a quarter | Rover mobility engineers; the NTRS references must be checked | It is the only hard requirement of the mobility scenario and removes two sites |
| E2 | Slope limit for building a base | ≤ 5°, failure at 10° | Lander and surface systems engineers | Removes 10 sites from the colony scenario |
| E3 | Whether the colony scenario should exist in its current form | Kept, all criteria labelled as proxies | Mission architects | The audit finds it close to "cold, polar, flat, quiet" rather than a lunar analog (finding K2) |
| E4 | Frozen-ground threshold for drilling and water | ≤ -6 °C, zero at 0 °C, from permafrost climatology [R32] | Permafrost scientists; drill engineers | Lunar polar ice is not permafrost; the proxy may be the wrong one entirely |
| E5 | Weights | Equal; each instrument counts for 1 in calibration | Mission and instrument teams, through a documented elicitation | Weights change rankings; no measured basis exists |
| E6 | Dry-air, wind, earthquake and thermal thresholds of the calibration scenario | Stated in `modes.ts` with "expert judgement" | Instrument teams | The whole calibration scenario rests on them |
| E7 | Lava tube evidence levels for the 29 sites not assessed, and the predisposition rule | 2 sites at level 3 from references; level 1 = basaltic Holocene volcano within 30 km | Volcanologists and speleologists | Separates demonstrated, probable and possible caves |
| E8 | Whether the south polar cap is the right lunar reference for each scenario | Whole cap south of 85°S | Lunar geologists; landing-site teams | The cap includes crater walls and shadowed floors that no mission would drive on; a landing-region reference may be more relevant |
| E9 | Which terrestrial materials are acceptable analogs of highland regolith and in which limits | None in the score; anorthosite sites (Mistastin) named in the text | Regolith and simulant specialists [R40, R41] | Needed before any material criterion is added |
| E10 | Independent list of expected analogs and negative controls | Team-written list, one negative control | Analog-site researchers outside the project | Without it the validation is circular |
| E11 | Confidence label thresholds (coverage 0.6 / 0.9, interval 15 / 30 points) | Presentation choices | Users of the tool | They change what users read as "reliable" |
| E12 | Treatment of reanalysis values more than 1 km off in elevation | Set to missing | Climatologists | Alternative: downscaling or station data |

## 4. Known weaknesses of the data

| Data | Weakness | Sites affected |
|---|---|---|
| Copernicus DEM | Edited flat over water and salt flats | Uyuni (flag `flat_artifact`); possibly sites with lakes in the window |
| Copernicus DEM | Surface model including vegetation and ice | Forested or glaciated windows |
| MODIS | One year (2024), 12 composites, clear sky only, one pixel | All; 19 sites with seasonal gaps; NDVI missing for 3 polar sites |
| NASA POWER | 50 km cell | 6 sites with climate values set to missing; all others corrected or used as is |
| USGS ComCat | Completeness varies even at M 4.5 in the early 2000s | Remote regions |
| Smithsonian GVP | Holocene only; one point per volcano | Basalt fields older than the Holocene cannot reach lava tube level 1 (Black Point lies 42 km from the nearest listed vent) |
| Candidate coordinates | Some marked approximate or "fixture coordinate" | Atacama, Changtang, Gobi, Qaidam, Lut, Hoggar, Harrat Khaybar, Peary Land |
| Candidate list | Hand-picked; known analogs over-represented | All results are relative to these 37 sites |

## 5. Biases

- **Selection bias**: the 37 sites were chosen by the team, mostly known analogs and cold, arid or volcanic places. Rankings say which of these 37 fit better, not where the best places on Earth are.
- **Geographic bias in data quality**: data gaps and approximations cluster at high latitude and high elevation. v2 shows them instead of scoring them, but a user may still read a high-coverage site as "better documented, therefore better".
- **Circular validation**: the expectations used to check rankings were written by the team that designed v1 (finding Va1).
- **Reviewer bias**: the audit, the corrections and the judged scores of the evaluation grid were produced by the same reviewer.

## 6. Interface

The interface was out of scope of this phase. It works with v2 but does not show the new outputs (confidence, coverage, bounds, failed requirements, explanation, flags) and shows raw identifiers for the new parameters, without unit. Its "See the match" panel still shows the v1 terrain values precomputed for the site images (30 m geographic grid), which differ slightly from the v2 values of the scorecard below it. A browser audit (`tools/validation/ui-audit/audit.mjs`, desktop and phone) found no functional defect with v2. Until it does, users of the website see less than the API provides. The needs are listed in [SCIENTIFIC_ROADMAP.md](SCIENTIFIC_ROADMAP.md), section 3.
