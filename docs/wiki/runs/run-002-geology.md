# run-002, geology dimension (T46, 20/11/2026)

The lithology of geological maps compared with the surface material of each lunar environment, for the 6.3 M cells of run-002.
- **Earth source:** Macrostrat `carto` tiles at zoom 8 (CC-BY 4.0), 20,307 tiles, 362 MB, 0 failures.
- **Crosswalk:** expert decision E17 ([methods/geology-crosswalk.md](../methods/geology-crosswalk.md)). David delegated it to Claude; it must be reviewed by lunar geologists before G5.
- **Sampling:** 9 samples per 5 km cell.
- **Release:** `r-51bfb3d5`, which supersedes `r-98f6eee4` and is the same run with geology added.

## Unfavourable results first

1. **Half of the assessed land has no usable lithology.**
   - No map unit: 29.2% of samples. Regions covered only by the 1:35M world map do not appear in the `carto` tiles: the Deccan, Tibet, the Gobi, Kamchatka.
   - Unit too generic, or mixed: 21.5 to 21.8% depending on the group ("intrusive igneous rocks", or a large unit listing many rock families).

   These are shown as unresolved, never as "no match".
2. **Matches are rare.**

   | | Highlands (anorthosite) | Maria (basalt) | Pits |
   |---|---|---|---|
   | match | 0.05% | 1.1% | none possible (E17) |
   | partial | 0.16% | 0.03% | 1.1% (basalt) |

3. **None of the 40 top slope zones of run-002 matches by geology.**
   - Dominant state: no match for 19 dossiers, unresolved for 17, no map for 4.
   - The two plausible places of run-002 are the same: Andrelândia is unresolved (the map unit is generic) and northern Skye is no match (its lavas are basalt, not anorthosite).
   - Slope and geology are reported side by side, never averaged (E5).
4. **Mistastin, the named anorthositic analog of v2, is "no match".** At 1:5M, the Geologic Map of North America shows only "undivided granitic rocks" in its cell. The anorthosite of the crater [R54, R55] is below the map's scale. Cells elsewhere in the same 1° tile (55–56°N, 62–63°W) do match.
5. **The first global run gave a false picture, fixed before this report.** Large undivided units of the Geological Map of the Arctic list "anorthositic gabbro" among granites. Under the first reading, most of the Canadian Shield was a highland match (11,501 cells, Pingualuit among them). The E17 amendment of 20/11 counts the lunar rock only when the map lists it first: 3,180 cells remain.

## Where the matches are

- **Highlands (3,180 cells with a majority of match samples):** the Grenville and Nain anorthosite massifs of Quebec and Labrador. Main 1° tiles: Lac-Saint-Jean (48–49°N 71–72°W), Havre-Saint-Pierre (50–52°N 64–65°W), Labrador (54–56°N 62–63°W). They come mostly from the Geologic Map of North America (2,666 cells).
- **Maria (67,639 cells):** the Paraná flood basalts (25–28°S 52–55°W), the Canary Islands and Madeira (27–32°N 14–19°W), and Iceland. The main maps are the Geological Map of the Arctic, South America 2018 and Europe 1:5M.

## Known places

| Place | Highlands | Maria | Map |
|---|---|---|---|
| Lac-Saint-Jean | match | no match | GMNA 1:5M ("plutonic: anorthosite") |
| Marcy massif (Adirondacks) | unresolved | no match | local map lists gneiss first |
| Holuhraun | no match | match | Iceland 1:500k |
| Craters of the Moon, Payunia | no match | match | |
| Mistastin | no match | no match | GMNA: granitic rocks (see above) |
| Pingualuit | unresolved | no match | Arctic map, mixed unit |
| Deccan, Tolbachik, Gobi, Qaidam, Changtang | no map | no map | world map only |

## What this cannot show

- **Mineralogy:** a lithology class is not a mineral composition. EMIT (52°N to 52°S) is not used yet.
- **Regolith mechanics:** grain size, cohesion and bearing capacity are not measured.
- **Rocks below the map's scale:** the small anorthosite bodies of impact structures, for example.
- **Cells under maps that do not exist in Macrostrat.**
