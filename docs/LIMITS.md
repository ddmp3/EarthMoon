# Limits and decisions that need experts

Full version (uncertainty table, data weaknesses, biases): [wiki/v2/SCIENTIFIC_LIMITATIONS.md](wiki/v2/SCIENTIFIC_LIMITATIONS.md). References `[Rn]`: [REFERENCES.md](REFERENCES.md).

## What a result does not mean

- That a site is equivalent to the Moon, or "X% similar".
- That it is a validated test site: only a field campaign by the team that will test can say so.
- Anything about the ground material. Lithology, mineralogy, grain size, regolith mechanics and dust are not measured yet.
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

## Decisions that need human expertise

Provisional choices, labelled `expert_judgement` in the API, until a named expert or a documented requirement settles them.

| # | Decision | Provisional choice | Who should decide |
|---|---|---|---|
| E1 | Rover climbing limit and required traversable share | 15° (VIPER; NTRS sources not yet re-verified), half the window | Rover mobility engineers |
| E2 | Slope limit to build a base | ≤ 5°, failure at 10° | Lander and surface systems engineers |
| E3 | Should the colony scenario exist as it is? | Kept, all criteria labelled as proxies | Mission architects |
| E4 | Frozen-ground threshold for drilling | ≤ -6 °C, zero at 0 °C [R32] | Permafrost scientists, drill engineers |
| E5 | Weights | Equal | Mission and instrument teams |
| E6 | Thresholds of the calibration scenario | In `modes.ts` | Instrument teams |
| E7 | Lava tube levels for 29 unassessed sites; the predisposition rule | 2 sites at level 3; level 1 = basaltic Holocene volcano within 30 km | Volcanologists, speleologists |
| E8 | Is the whole polar cap the right lunar reference? | Everything south of 85°S | Lunar geologists, landing-site teams |
| E9 | Which Earth materials are acceptable highland regolith analogs | None in the score | Regolith and simulant specialists [R40, R41] |
| E10 | Independent list of expected analogs and negative controls | Team-written, one negative control | Analog researchers outside the project |
| E11 | Confidence label thresholds | Coverage 0.6 / 0.9, interval 15 / 30 points | Users of the tool |
| E12 | Reanalysis values more than 1 km off in elevation | Set to missing | Climatologists |
