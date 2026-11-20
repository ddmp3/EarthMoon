# Limits and decisions that need experts

Full version (uncertainty table, data weaknesses, biases): [wiki/v2/SCIENTIFIC_LIMITATIONS.md](wiki/v2/SCIENTIFIC_LIMITATIONS.md). References `[Rn]`: [REFERENCES.md](REFERENCES.md).

## What a result does not mean

- That a site is equivalent to the Moon, or "X% similar".
- That it is a validated test site: only a field campaign by the team that will test can say so.
- Much about the ground material. v3 compares the **lithology class** of geological maps (T46). A lithology class is not a mineralogy, and a mineralogy is not regolith mechanics: grain size, cohesion, bearing capacity and dust are not measured. Where the map has no unit or only a generic class, geology is "no map" or "unresolved", never "no match".
- Anything below the 40 m DEM scale: rocks, small craters, the slope under a wheel.
- That a site without a lava tube level has no cave: it was **not assessed**.
- That few earthquakes means a quiet site for a seismometer, or that a high latitude reproduces lunar polar lighting.

**Earth cannot reproduce:**
- lunar gravity (one sixth);
- vacuum and the absence of weather;
- the radiation environment [R46];
- the cold of shadowed regions (below 110 K [R1]);
- dust behaviour in vacuum [R11].

## Main uncertainties

- Sites are single points, and several coordinates are approximate.
- Wind, humidity, precipitation and MODIS values have no sigma, so the intervals are lower bounds.
- Correlated errors are ignored, and the choice of criteria is not varied.
- The 37 sites were hand-picked: rankings compare these sites, not the whole Earth.
- The eight v2 terrain metrics carry one independent property, slope (Spearman 0.87 to 0.99 on 71,731 lunar and 1,410 random Earth windows); detrended roughness behaves differently on the two bodies. See [wiki/methods/parameters.md](wiki/methods/parameters.md).

## Decisions that need human expertise

Provisional choices, labelled `expert_judgement` in the API, until a named expert or a documented requirement settles them.

| # | Decision | Provisional choice | Who should decide |
|---|---|---|---|
| E1 | Rover climbing limit and required traversable share | 15° (VIPER). Checked 18 Nov 2026: **not stated** in the NTRS abstracts (slides not readable). Apollo LRV: 20 to 23°, max 25° (verified, NTRS 20250011301). Half the window | Rover mobility engineers |
| E2 | Slope limit to build a base | ≤ 5°, failure at 10° | Lander and surface systems engineers |
| E3 | Should the colony scenario exist as it is? | v2: kept, all criteria labelled as proxies. v3: replaced by scenario A ([SCENARIOS.md](SCENARIOS.md)), to be reviewed | Mission architects |
| E4 | Frozen-ground threshold for drilling | ≤ -6 °C, zero at 0 °C [R32] | Permafrost scientists, drill engineers |
| E5 | Weights | v2: equal. v3: no weights; dimensions are reported separately, and a global value is their minimum (T23) | Mission and instrument teams |
| E6 | Thresholds of the calibration scenario | In `modes.ts` | Instrument teams |
| E7 | Lava tube levels for 29 unassessed sites; the predisposition rule | 2 sites at level 3; level 1 = basaltic Holocene volcano within 30 km | Volcanologists, speleologists |
| E8 | Is the whole polar cap the right lunar reference? | Everything south of 85°S | Lunar geologists, landing-site teams |
| E9 | Which Earth materials are acceptable highland regolith analogs | None in the score | Regolith and simulant specialists [R40, R41] |
| E10 | Independent list of expected analogs and negative controls | Team-written, one negative control | Analog researchers outside the project |
| E11 | Confidence label thresholds | Coverage 0.6 / 0.9, interval 15 / 30 points | Users of the tool |
| E12 | Reanalysis values more than 1 km off in elevation | Set to missing | Climatologists |
| E13 | Base site requirements beyond slope (bearing capacity, boulder density, landing hazards) | Not assessed: no Earth or lunar layer in the catalogues measures them | Lander and surface systems engineers |
| E14 | Mars rover mobility limit per terrain | R43 abstract (read 18 Nov 2026): up to 22° on smooth bedrock, 28° on some cohesive soils, embedding at 17° in loose sand. Which applies needs the terrain type, which no global layer gives | Mars rover mobility engineers |
| E15 | Site requirements of each instrument in scenario C | None set; every instrument row is marked as an open requirement | Instrument teams |
| E16 | Which planetary environment each scenario targets | Proposed in [SCENARIOS.md](SCENARIOS.md) from the T20 environments (refines E8) | Lunar and Mars landing-site teams |
| E17 | Which Earth lithologies match the lunar highlands, maria and pits | Crosswalk of [wiki/methods/geology-crosswalk.md](wiki/methods/geology-crosswalk.md). Delegated by David to Claude on 20/11/2026; to be reviewed before G5 | Lunar geologists, planetary sample scientists |
