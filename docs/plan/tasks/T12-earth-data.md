# T12 Earth data inventory

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, and `docs/plan/tasks/T10-moon-data.md` (same output format). Branch: `docs/T12-earth-data`. Research task.

## Goal
A verified catalogue of global (or wide-coverage) Earth data that can be compared with lunar and Martian properties, or that is needed to mask, qualify or explain a result.

## Context
- v2 uses Copernicus DEM GLO-30 (terrain at 40 m), MODIS LST and NDVI (one pixel, 2024), NASA POWER (50 km climatology), USGS ComCat (M ≥ 4.5), and Smithsonian GVP. Details: `docs/SCIENTIFIC_REFERENCES.md` section 7.
- Discovery (decision 6.3) needs global layers at a known scale, plus masks: water, vegetation, urban areas, ice.

## Candidates to check (each fact verified at the source)
| Dimension | Candidates |
|---|---|
| Topography | Copernicus GLO-30 and GLO-90; NASADEM / SRTM; ArcticDEM; REMA; ICESat-2 (ATL06, ATL08); GEDI (where relevant) |
| Optical and thermal | MODIS (LST, NDVI, albedo, emissivity); ASTER (L2, Global Emissivity Database); Landsat Collection 2; Sentinel-2 L2A; EMIT L2B mineralogy |
| Radar | Sentinel-1 GRD; RADARSAT-1 archive and RCM (CSA, listed in the challenge resources) |
| Climate | ERA5 and ERA5-Land; NASA POWER; CHELSA or WorldClim 1 km climatologies; Global Aridity Index |
| Ice and water | Permafrost (Obu et al. 2019; ESA CCI Permafrost); Randolph Glacier Inventory; JRC Global Surface Water |
| Land cover and soil | ESA WorldCover; SoilGrids 2.0 |
| Geology | GLiM; Macrostrat; OneGeology; national geological surveys |
| Features | Impact structures (Earth Impact Database or another curated list); Smithsonian GVP; caves and lava tubes (no global database expected: list national or regional sources and karst maps) |
| Geophysics | USGS ComCat; seismic station noise (IRIS / EarthScope) |
| Aeolian | Dust and aerosol (MODIS AOD, MERRA-2 dust) |
| Access and logistics | Optional: roads, settlements. Only for operational suitability, never for similarity |

Where: NASA Earthdata (CMR), Copernicus Data Space, AWS Open Data, Microsoft Planetary Computer, ESA CCI, JAXA G-Portal, CSA open data, the producer of each data set.

## Outputs
- `data/catalog/earth.yaml` (same schema; add `licence` and `attribution` as required fields).
- `docs/wiki/data/earth.md`: table plus one page of synthesis, with:
  - the volume of data needed for a global run at each scale (rough, sourced);
  - which layers serve similarity, which serve masks, and which serve operations.

## Done when
Every candidate has an entry with a status, and licences and attributions are recorded. Checks pass.

## Pitfalls
- Copernicus DEM is a surface model (vegetation, buildings, and flattened water and salt flats).
- MODIS LST is clear-sky only.
- Do not add a layer because it exists: say which dimension it serves.
