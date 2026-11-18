# Earth data: what can be compared, masked or used to qualify

Synthesis of task T12 (18 November 2026). Source catalogue: `data/catalog/earth.yaml`.
- **41 products at T12; 44 after T14** ([coverage review](coverage-review.md)): Antarctic rock outcrops and geology, FABDEM added.
- Every entry states its licence, its attribution and its **use**: similarity, mask, qualification or operations.

Full table: [earth-table.md](earth-table.md).

## By dimension

| Dimension | Similarity layers (compared with a planetary property) | Masks and qualification | Scale |
|---|---|---|---|
| Topography | Copernicus DEM GLO-30 (global, 30 m) and GLO-90 (90 m, for the coarse screening); ArcticDEM and REMA (2 m); NASADEM (30 m, 60°N to 56°S, independent check) | ICESat-2 ATL06/ATL08 and GEDI tracks to measure DEM bias (surface model vs ground) | 2 m to 90 m |
| Geology | GLiM (open version gridded at 0.5°; polygon version to locate); Macrostrat (CC-BY, multi-scale, live API to freeze) | OneGeology (not verified) | 50 km to map scale |
| Mineralogy, composition | EMIT L2B minerals (60 m, 52°N to 52°S, interpretation); ASTER GED emissivity (100 m, silica indicator) | Landsat, Sentinel-2 reflectance | 60 m to 100 m |
| Thermal | MODIS LST (1 km, 8-day; **Terra ends 1 December 2026**); MCD43A3 albedo; ERA5-Land (9 km, model) | Permafrost ground temperature (model, 1 km, RMS 2 °C) | 1 to 9 km |
| Ice and water | Permafrost probability (Obu et al., ESA CCI v5); RGI 7.0 glaciers | JRC Global Surface Water (water mask) | 30 m to 1 km |
| Dust and atmosphere | MCD19A2 aerosol optical depth (1 km, daily); ERA5 (0.25°) | MERRA-2 dust (not verified) | 1 to 30 km |
| Vegetation and land cover | — | ESA WorldCover (10 m, 74 to 77% overall accuracy) and NDVI, as masks only | 10 m to 500 m |
| Soil | — | SoilGrids (250 m, model, poor in deserts and polar areas) for qualification only | 250 m |
| Subsurface (caves, lava tubes) | **No global source** | Smithsonian GVP for predisposition only; karst map (not verified) | — |
| Geophysics | — | USGS events (regional seismicity); EarthScope MUSTANG station noise (sparse) | Stations |

## Findings for the method (inputs to T20 to T22)

1. **Search scales.**
   - **Global screening:** Copernicus GLO-90.
   - **Refinement:** GLO-30.
   - **Operational scale (2 m):** only in the Arctic and Antarctica (ArcticDEM, REMA). Elsewhere, rover-scale terrain needs national lidar.
   - Mars has 1 to 2 m HiRISE DTMs at many sites; the Moon has 5 m at the south pole only.
2. **The DEMs are surface models.** Copernicus DEM, ArcticDEM and REMA all include vegetation, buildings or ice. Vegetated areas are masked anyway, but snow and ice surfaces need a flag.
3. **Composition is the weak dimension.**
   - The open GLiM grid is 0.5°, too coarse for small anorthosite bodies like Mistastin.
   - EMIT excludes the poles.
   - The geology dimension (T46) depends on finding the polygon version of GLiM or on Macrostrat coverage.
4. **Caves cannot be discovered** from global open data. Lava tube evidence stays a curated, referenced list (expert decision E7).
5. **Model vs measurement.** ERA5, ERA5-Land, CHELSA, WorldClim, the permafrost maps and SoilGrids are models. The catalogue labels them, and the comparison must too.
6. **Continuity.** Terra MODIS observations end on 1 December 2026. Multi-year statistics up to then stay valid; any later update needs Aqua or another sensor.
7. **Volume.** Some sizes are stated: ArcticDEM mosaic 17 TB, REMA mosaic 8.4 TB, EMIT 21 TB, GEDI 109 TB. The global GLO-30 size is not stated on the pages read. **Measure it in T22** before sizing the pipeline.

## Licences to check before redistribution

- Sentinel-1 and Sentinel-2: the Copernicus legal notice was not read.
- CHELSA and WorldClim: no licence stated on the pages read.
- RCM: own user licence agreement, public tier over Canada only.
- ESA CCI Permafrost: licence not stated.
- SoilGrids: CC-BY, but the REST API is paused.

## Not verified (needs a browser)

- Global Aridity Index v3: now v3.1, verified (verified 18/11 in T14, see [coverage review](coverage-review.md));
- OneGeology;
- Earth Impact Database;
- MERRA-2 dust;
- WOKAM karst map;
- the RADARSAT-1 archive;
- the Smithsonian GVP terms (the site refused automated access today; v2 used and froze its data on 17 November).
