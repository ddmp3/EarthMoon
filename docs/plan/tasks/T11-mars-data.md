# T11 Mars data inventory

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, and `docs/plan/tasks/T10-moon-data.md` (same output format). Branch: `docs/T11-mars-data`. Research task.

## Goal
The same verified catalogue as T10, for Mars. Mars is an independent analysis: an atmosphere, dust, past water, ice and sediments make it a different problem. Lunar criteria are never reused with new weights (mission rule).

## Mars topics to cover
Geology and mineralogy; sedimentary deposits; volcanic terrain; ancient aqueous environments (clays, sulfates, chlorides); aeolian processes and dunes; dust; temperature and thermal inertia; ground ice and polar deposits; subsurface (radar, caves); terrain for mobility and landing.

## Candidates to check (each fact verified at the source)
- **Topography:** MGS MOLA (MEGDR, PEDR); Mars Express HRSC DTMs; MOLA-HRSC blended DEM (USGS); MRO CTX global mosaic and CTX DTMs; HiRISE images and DTMs.
- **Thermal:** Mars Odyssey THEMIS (day and night IR mosaics, thermal inertia); MGS TES (albedo, dust cover index, thermal inertia).
- **Composition:** MRO CRISM (mineral parameter maps, MTRDR); Mars Express OMEGA; Odyssey GRS (H, Cl, Fe, K).
- **Subsurface:** SHARAD, MARSIS.
- **Atmosphere and climate:** Mars Climate Database (LMD; model), MCS.
- **Ice:** SWIM subsurface ice maps.
- **Maps and catalogs:** USGS global geologic map (Tanaka et al. 2014); crater database (Robbins and Hynek); cave candidate catalog (USGS); landing site data sets.
- **Other agencies:** Emirates Mars Mission; Tianwen-1 (check whether access is open).

Where: PDS Geosciences Node (Mars ODE), PDS Imaging, USGS Astrogeology, ESA PSA, Murray Lab (CTX mosaic), LMD (MCD).

## Outputs
- `data/catalog/mars.yaml` (same schema as `moon.yaml`; the shared schema test must cover it).
- `docs/wiki/data/mars.md`: table plus one page of synthesis listing which Mars environments can be profiled (T20) and the main traps.

## Done when
Every candidate above has an entry with a status. The synthesis lists the Mars environments that can be profiled and their products. Checks pass.

## Pitfalls
- CRISM detections are interpretations of spectra: mark them `interpretation`.
- Mars Climate Database values are model output: mark them `model`.
