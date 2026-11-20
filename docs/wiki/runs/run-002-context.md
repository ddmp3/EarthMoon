# run-002, Earth context: frozen ground and aridity (T47, 20/11/2026)

Two Earth-side context layers for the 6.3 M cells of run-002, under decision E18 ([methods/thermal-hydric.md](../methods/thermal-hydric.md)). They say what an Earth place offers for a test. **They are not comparisons with the Moon**, and they are never averaged with slope or geology.

| Layer | Source | Class | Sigma |
|---|---|---|---|
| Frozen ground (E4: -6 °C or colder) | Obu et al. 2018, 1 km, north of 25°N (CC-BY 3.0, PANGAEA) | model | model spread (MAGTSTD), not interannual |
| Aridity index | Global Aridity Index v3.1, 1 km, 1970 to 2000 (CC BY 4.0 per the figshare API; MD5 checked) | model | none |
| Surface thermal cycling | MODIS land surface temperature | direct | **not computed**: waits for a NASA Earthdata account (data improvement D1) |

## Unfavourable results first

1. **No thermal comparison with the Moon.** The within-planet quantile match was rejected (E18). Surface thermal cycling, the only thermal parameter of scenario A, waits for its data.
2. **Frozen ground covers only 41.7% of the cells**, those north of 25°N. The south (Antarctica, Patagonia, the Andes) is "not covered", not "not frozen" (data improvement D9).
3. **15.8% of cells have no aridity value.** Antarctica lies outside the file, and the file writes 0 both over the sea and for an index below 0.0001; 0 is treated as no data (D11). Atacama still has a value (0.0049, hyper-arid).
4. **The 40 top slope zones are neither frozen nor dry** (their cells, counted once per dossier).
   - Frozen ground: 0 cells meet E4. 10 are partial, 60 not met, 146 not covered.
   - Aridity: 150 humid, 48 semi-arid, 12 dry sub-humid and 6 arid cells.

## Results

| | met (≤ -6 °C) | partial (-6 to 0 °C) | not met | not covered |
|---|---|---|---|---|
| Frozen ground, share of cells | 3.8% | 5.5% | 32.5% | 58.3% |

| hyper-arid | arid | semi-arid | dry sub-humid | humid | no data |
|---|---|---|---|---|---|
| 6.3% | 14.8% | 14.0% | 7.6% | 41.6% | 15.8% |

**Known sites:**
- **Frozen ground met:** Haughton (-12.6 °C), Tunnunik, Axel Heiberg, Peary Land, Popigai.
- **Partial:** Svalbard, Pingualuit, Elgygytgyn, Tolbachik, Changtang.
- **Hyper-arid:** Atacama, Death Valley, Qaidam, Namib, Aorounga, Tenoumer.
- **No aridity value:** the Dry Valleys and Erebus (Antarctica, outside the file).

## What this cannot show
- Lunar temperatures, ice content, or how a material behaves in vacuum.
- Current conditions: aridity is a 1970 to 2000 climatology, ground temperature a 2000 to 2016 mean.
- A measurement at the site: both layers are models.
