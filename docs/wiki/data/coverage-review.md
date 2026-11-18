# Data coverage review (T14, 18/11/2026)

Purpose: check the catalogues against what the discovery method needs now that T40 has run on real data. Every fact added was read at its source page. Pages that refuse automated reading stay "not verified" until someone reads them in a browser.

## Gaps found

| Need | Body | Gap | Action |
|---|---|---|---|
| Water and ice mask | Earth | WorldCover has no tile south of 60°S: 7,042 of 26,475 elevation tiles (27%) had no mask (T40) | Added `add-rock-outcrop-v7-3`: rock outcrops of Antarctica (verified). Outside the outcrops is ice or snow |
| Lithology | Earth | GLiM (0.5°) and Macrostrat are coarse or empty on Antarctica, the closest cold-desert analog area | Added `scar-geomap-v2022-08`: 1:250,000, 99,080 polygons (verified) |
| Effect of trees and buildings on slope | Earth | Copernicus is a surface model: forests and buildings can create slope and roughness | Added `fabdem-v1-2` for qualification (verified; non-commercial licence) |
| Aqueous minerals | Mars | OMEGA and CRISM products are raw or per-observation; no ready map of clays, sulfates and carbonates | Added `mocaas-2023`: global map of 5 mineral classes, ±70° (verified; licence not stated) |
| Chlorides (Atacama-type analogs) | Mars | No chloride source | Added `osterloo-chlorides-leask-ehlmann-2021` (partly verified) and `cassis-chloride-candidates-2024` (not verified, pages refused) |
| Mineralogy | Moon | `mineral_class` has no Moon source | Added `kaguya-mi-mineral-maps` (not verified: USGS page refused) |
| Lithology | Mars | Geologic map not verified | `usgs-mars-geologic-map-2014` now partly verified (usgs.gov page) |

## Still not verified, and blocking a kept parameter

These need a person to open the page in a browser (the hosts refuse automated reading):

| Entry | Parameter | Page |
|---|---|---|
| `usgs-unified-geologic-map` | `lithology_class` (Moon) | astrogeology.usgs.gov, unified geologic map of the Moon |
| `usgs-mars-geologic-map-2014` | `lithology_class` (Mars): GIS files and unit attributes | pubs.usgs.gov/sim/3292 |
| `ody-themis-mosaics-ti` | `thermal_inertia` (Mars, 100 m) | astrogeology.usgs.gov, THEMIS thermal inertia mosaic |
| `kaguya-mi-mineral-maps` | `mineral_class` (Moon) | astrogeology.usgs.gov, Kaguya MI 59 mpp |
| `cassis-chloride-candidates-2024` | `mineral_class` (Mars) | doi.org/10.1038/s41597-024-03685-3 |
| `global-aridity-index-v3` | none kept (context) | figshare 7504448 |

## Not added

- Antarctic climate and permafrost are already covered by ERA5-Land and ESA CCI Permafrost (Antarctica products listed).
- No global Earth mineral map exists beyond EMIT (52°N to 52°S). Hyperspectral missions (EnMAP, PRISMA) acquire on request: not a global layer.
- Mineral maps of Mars and the Moon are presence classes, not abundances: compared as classes (T21 rule).

## Parameters

Proposed changes to `data/parameters.yaml`, to apply only once the entries are verified:
- `lithology_class`, Earth: add `scar-geomap-v2022-08` (verified now).
- `mineral_class`, Mars: add `mocaas-2023`.
- `mineral_class`, Moon: add `kaguya-mi-mineral-maps` once verified.
- Mask south of 60°S: `add-rock-outcrop-v7-3`, in T40 or T43.
