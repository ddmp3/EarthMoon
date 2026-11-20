# Thermal, ice and aridity dimensions (T47, decision E18)

**Status: E18 accepted by David on 20/11/2026: no quantile match, three labelled context layers. Frozen ground and aridity first; surface thermal cycling waits for the Earthdata account (data improvement D1).**

## Why there is no thermal "match"
- Lunar surface temperatures have no Earth equivalent:
  - shadowed regions stay below 110 K and reach 29 K [R1];
  - the equatorial day-night swing is about 300 K [R12].
- A quantile match within each planet was proposed in `tools/analog_backend`: an Earth place in the top 10% of Earth amplitudes would "resemble" a lunar place in the top 10% of lunar amplitudes. The proposal is to **reject it**. It has no physical basis: equal rank does not mean that a material, an instrument or a process behaves the same way (T23).
- So the three dimensions are **reported as Earth-side context layers, each with its class and what it does not mean**. They are not typicalities against the Moon, and they are never averaged with slope or geology (E5).

## Parameters

| Layer | Class | What it says | What it does not mean | Source (status) |
|---|---|---|---|---|
| Surface thermal cycling | direct (satellite) | mean day-night swing of the land surface temperature, multi-year, with its interannual sigma | not a lunar temperature; not regolith thermal inertia | MODIS land surface temperature (verified; Earthdata account needed) |
| Frozen ground | model | modelled mean annual ground temperature and permafrost probability, Northern Hemisphere | not lunar ice; not ice content; not a measurement at the site | Obu et al. 2018, 1 km (verified, CC-BY 3.0) |
| Aridity | model (index) | ratio of precipitation to potential evapotranspiration | not the absence of water in the ground; not lunar dryness | Global Aridity Index v3, 1 km (verified; non-commercial use) |

**Rules carried from v2 findings:**
- a value modelled from other data is labelled "model" on the map and in the zone card;
- no elevation correction is applied to minimum temperatures, because valleys can hold inversions (finding L9);
- every multi-year statistic carries its interannual sigma (finding L5);
- frozen ground is used as context for drilling tests only, with the existing threshold E4 (≤ −6 °C).

## Decisions for David
1. **E18, method.** Should the quantile match be rejected, with the three dimensions kept as labelled context layers (not similarities)?
2. **Access to surface temperature.** MODIS (the only multi-year surface temperature source with a sigma) and ERA5-Land need a free account: NASA Earthdata and the Copernicus CDS. Options:
   - create the accounts and put the credentials in a local file that is never committed, as ADR-009 planned;
   - or do without thermal cycling for now: frozen ground and aridity need no account.
