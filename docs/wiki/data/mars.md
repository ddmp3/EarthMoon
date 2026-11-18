# Mars data: what can be profiled now

Synthesis of task T11 (18 November 2026). Source catalogue: `data/catalog/mars.yaml` (26 products: 7 verified, 11 partly verified, 8 not verified). Full table: [mars-table.md](mars-table.md). Mars is analysed on its own terms: lunar criteria are never reused with new weights.

## Environments and the products that can describe them

| Environment (T20) | Delineation (mask) | Terrain | Other dimensions | Can be profiled now? |
|---|---|---|---|---|
| Ice-rich mid-latitudes | SWIM ice consistency map (3 km, interpretation, 0 to 60°N; south not read) | MOLA MEGDR; HiRISE DTMs where available | Neutron flux (Odyssey); SHARAD radargrams; TES thermal inertia | **Yes**, with SWIM as an interpretation, not an ice measurement |
| Polar layered deposits | Latitude plus MOLA polar grids (up to 512 ppd) | MOLA polar grids | SHARAD (and 3D volumes), MARSIS | **Yes** for terrain and radar |
| Ancient aqueous terrain (clays, sulfates, chlorides) | OMEGA / CRISM hydrated mineral detection sites (interpretation) | HiRISE DTMs (1 to 2 m) at targeted sites; MOLA | CRISM targeted cubes; GRS Cl and water (5° bins) | **Partly**: detections are sites, not a continuous map |
| Sedimentary basins (landing sites such as Jezero, Gale) | Needs the geologic map (not verified) | HiRISE DTMs; CTX 5 m mosaic | CRISM | **Partly** |
| Volcanic plains | Needs the geologic map (not verified) | MOLA, CTX, HiRISE | TES thermal inertia | **Partly** |
| Dune fields | Needs a dune catalogue (not inventoried yet) | HiRISE, CTX | Thermal inertia, Climate Database winds (model) | **No**, the mask is missing |
| Caves and skylights | Cave candidate catalogue (not verified) | HiRISE DTMs | THEMIS night IR (not verified) | **No**, until the catalogue is verified |

## What Mars offers that the Moon does not (here)

- **Rover-scale terrain:** 1,377 HiRISE DTMs at 1 to 2 m post spacing, with vertical precision in the tens of centimetres. On the Moon, the comparable public products are the 5 m south pole mosaic and 50 preliminary NAC DTMs. Terrain comparison at the operational scale (T22) is therefore possible for many Martian sites.
- **An atmosphere and dust:**
  - Mars Climate Database (model; free for scientific use, with registration);
  - Mars Climate Sounder profiles (measured and derived).
  Wind, dust and temperature are comparable in kind with Earth, unlike on the Moon.

## Traps found while checking

1. **Interpretation vs measurement.** SWIM is a consistency index built with thresholds from several data sets. OMEGA and CRISM hydrated maps show detection sites. Neither is an abundance.
2. **Effective resolution.** MOLA grids are binned from tracks, so the high-resolution cells can be empty or interpolated, as with LOLA. TES thermal inertia masks its interpolated cells.
3. **Coarse composition.** GRS elements come in 2° to 10° bins: hundreds of kilometres.
4. **Model output.** The Mars Climate Database is a general circulation model, linearly interpolated.
5. **Access.** The HRSC team site was unreachable; the ESA PSA FTP path asked for authentication; the EMM portal rendered no text. Tianwen-1 has no official release page that we could read.

## To finish before gate G1 (needs a browser)

- Geologic map of Mars (Tanaka et al. 2014);
- Robbins and Hynek crater database;
- the cave candidate catalogue;
- MOLA-HRSC blended DEM;
- THEMIS mosaics and thermal inertia;
- TES albedo and dust cover index;
- EMM and Tianwen-1 access;
- a dune field catalogue (not yet inventoried).
