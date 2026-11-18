# Lunar data: what can be profiled now

Synthesis of task T10 (18 November 2026). Source catalogue: `data/catalog/moon.yaml` (35 products: 10 verified, 16 partly verified, 9 not verified). Full table: [moon-table.md](moon-table.md). Each fact in the catalogue was read at its source page; "not verified" means the page could not be read, not that the product is bad.

## Environments and the products that can describe them

| Environment (T20) | Delineation (mask) | Terrain | Other dimensions | Can be profiled now? |
|---|---|---|---|---|
| Polar highlands, lit | Permanent shadow and average illumination maps (PGDA, model, 60 to 240 m) | LDEM_85S_40M (v2), 5 m mosaic 87°S to 90°S | Illumination (model); Diviner polar resource products (model); LAMP albedo; Mini-RF CPR | **Yes** for terrain and illumination. Thermal and volatiles only partly verified |
| Permanently shadowed regions | Same permanent shadow map | Same (LOLA is an active laser, so it measures inside shadow) | LAMP H2O absorption depth; Diviner ice stability depth (model); LEND neutrons; Mini-RF CPR; Chandrayaan-2 DFSAR | **Yes** for terrain; volatiles are indicators, not abundances |
| Persistently lit ridges | Average illumination map (model) | Same | Illumination | **Yes** |
| Mare plains | Needs a geologic map (USGS 1:5M, verified in T14) or a composition threshold (Lunar Prospector FeO, 0.5° bins) | SLDEM2015 (60°S to 60°N, about 60 m) and its slope maps | LP FeO/Th; M3 reflectance; SELENE MI/SP | **Partly**: terrain yes; geologic map verified in T14 |
| Pits and lava tubes | LROC pit atlas (list not yet read) | NAC stereo DEMs at selected sites (50 public, preliminary) | SELENE radar sounder; GRAIL gravity (exploratory for caves) | **Partly**: a set of sites, not a distribution |
| Fresh and degraded craters, ancient terrain | Needs a crater database (Robbins 2019) or geologic map ages: **both not verified** | SLDEM2015 | — | **No**, until those sources are verified |

## Traps found while checking

1. **Effective resolution (finding L3).** The polar grids are interpolated between laser tracks. The 5 m mosaic ships a **count map** (returns per pixel). It can measure where the 40 m grid really has data, which is the input T20 and T22 need to quantify the bias.
2. **Models presented next to measurements.** Illumination, permanent shadow and the Diviner ice stability depth are computed, not observed. The catalogue marks them `model`.
3. **Volatile indicators are not abundances:**
   - LEND gives neutron count ratios;
   - LAMP gives an absorption depth;
   - Mini-RF CPR also responds to surface roughness;
   - Lunar Prospector hydrogen is "not necessarily reliable" where thorium is high.
4. **M3 Level 2** is not corrected to ground truth, and its thermal removal is a model step.
5. **Access:**
   - Chandrayaan-2 downloads sit behind a login;
   - the access conditions of the Chang'e system are unknown (its page needs a browser);
   - the JAXA DARTS search is suspended, although the PDS3 directories are listed openly;
   - Mini-RF releases are delayed, and its mosaic volume is called "global" by one page and "poleward of 70°" by another.
6. **Composition is coarse.** Global element maps are 0.5° to 5° bins, which is 15 to 150 km. Fine mineralogy (M3, about 95% coverage; Chandrayaan-2 IIRS, 80 m) needs careful processing before any comparison.

## To finish before gate G1 (needs a browser)

USGS hosts and the publisher Wiley refused automated access. David, or a reviewer, please check in a browser and fill in the catalogue:

- the Unified Geologic Map of the Moon (USGS, 1:5M, 2020): format and licence (verified 18/11 in T14, see [coverage review](coverage-review.md));
- the Robbins 2019 crater database: data host, minimum diameter, format;
- the Chang'e data release system: products, and whether foreign users can register;
- the LROC WAC global mosaic and the GLD100 product pages;
- the Diviner polar temperature maps directory (TLS error), and the location of the rock abundance and H-parameter maps.
