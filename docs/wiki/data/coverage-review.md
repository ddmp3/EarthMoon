# Data coverage review (T14, 18/11/2026)

Purpose: check the catalogues against what the discovery method needs now that T40 has run on real data. Every fact added was read at its source page. Pages that refuse automated reading stay "not verified" until someone reads them in a browser.

## Gaps found

| Need | Body | Gap | Action |
|---|---|---|---|
| Water and ice mask | Earth | WorldCover has no tile south of 60°S: 7,042 of 26,475 elevation tiles (27%) had no mask (T40) | Added `add-rock-outcrop-v7-3`: rock outcrops of Antarctica (verified). Outside the outcrops is ice or snow |
| Lithology | Earth | GLiM (0.5°) and Macrostrat are coarse or empty on Antarctica, the closest cold-desert analog area | Added `scar-geomap-v2022-08`: 1:250,000, 99,080 polygons (verified) |
| Effect of trees and buildings on slope | Earth | Copernicus is a surface model: forests and buildings can create slope and roughness | Added `fabdem-v1-2` for qualification (verified; non-commercial licence) |
| Aqueous minerals | Mars | OMEGA and CRISM products are raw or per-observation; no ready map of clays, sulfates and carbonates | Added `mocaas-2023`: global map of 5 mineral classes, ±70° (verified; licence not stated) |
| Chlorides (Atacama-type analogs) | Mars | No chloride source | Added `cassis-chloride-candidates-2024`: 965 candidates, CaSSIS covers 7.1% of the surface (verified) and `osterloo-chlorides-leask-ehlmann-2021` (partly verified) |
| Mineralogy | Moon | `mineral_class` has no Moon source | Added `kaguya-mi-mineral-maps`: plagioclase, olivine, pyroxenes in wt%, 59 m, ±50° (verified) |
| Lithology | Moon, Mars | Geologic maps not verified | `usgs-unified-geologic-map` (CC0, global, 1:5M) and `usgs-mars-geologic-map-2014` (1:20M, GIS 790 MB) verified |
| Aridity | Earth | Version 3.0 in the catalogue | Version 3.1 supersedes it: v3.0 had a dry bias (net longwave error) |

The pages of USGS, figshare and nature.com refuse automated reading. David read them in a browser on 18/11/2026 (the copied text is kept outside git, in `earthmoon-data/sources/2026-11-18-coverage-review-text.txt`).

## Still not verified, and blocking a kept parameter

| Entry | Parameter | Status |
|---|---|---|
| `ody-themis-mosaics-ti` | `thermal_inertia` (Mars, 100 m) | USGS product page returns 404; TES thermal inertia (global, verified) remains the source |

## Not added

- Antarctic climate and permafrost are already covered by ERA5-Land and ESA CCI Permafrost (Antarctica products listed).
- No global Earth mineral map exists beyond EMIT (52°N to 52°S). Hyperspectral missions (EnMAP, PRISMA) acquire on request: not a global layer.
- Mineral maps of Mars and the Moon are presence classes, not abundances: compared as classes (T21 rule).

## Parameters

Applied on 18/11/2026 with David's agreement:
- `lithology_class`, Earth: `scar-geomap-v2022-08` added.
- `mineral_class`, Mars: `mocaas-2023` added.
- `mineral_class`, Moon: `kaguya-mi-mineral-maps` added (verified, ±50° only).
- Mask south of 60°S: `add-rock-outcrop-v7-3`, to wire into the feature cube (T43).
- Licences: FABDEM (non-commercial) and MOCAAS (licence not stated) approved by David; EarthMoon is not commercial.
