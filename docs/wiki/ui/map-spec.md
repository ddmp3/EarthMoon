# Map interface specification (T26)

Method: [../methods/mapping.md](../methods/mapping.md). Built in T45.

**Style:** keep the existing design.
- Dark theme, with the tokens of `apps/web/src/styles.css`: `--bg`, `--panel`, `--line`, `--text`, `--muted`, `--accent`, `--off`.
- Space Grotesk for titles, Inter for text.
- The pastel hatching `#b9c6e8` from v2 is the colour of the **coverage overlay** (below).

## Main screen

```
+---------------------------------------------------------------------------------+
| EarthMoon   Scenario [B Robotic lunar v]  Environment [Lit polar highlands v]   |
+-------------------+-------------------------------------------------------------+
| LAYERS            |                                                             |
| (o) Topography    |                     world map (cells)                       |
| ( ) Geology  wait |                                                             |
| ( ) Thermal  wait |     ####  value colour (cividis)                            |
| ( ) Operational   |     ////  partial: pastel hatching                          |
| ( ) Multidim. --  |     ....  not evaluated: grey dots                          |
|   (needs 2 dims)  |     xxxx  masked: outline only                              |
| [x] Confidence    |                                                             |
| [x] Coverage      |     ////  coverage overlay (on/off): where data are missing |
|     overlay  (i)  |           or weak; (i) opens "Data and method"            |
|                   |                                                             |
| ZONES  tau [0.5v] | +--------------------------+                                |
| min area [3 v]    | | legend: typicality 0..1  |                                |
| 1. zone 12  0.81  | | "as typical as X% of the |                                |
| 2. zone 4   0.77  | |  most central windows"   |                                |
| [compare 2-4]     | | 4 states, with patterns  |                                |
+-------------------+-------------------------------------------------------------+
| Earth cannot reproduce: gravity, vacuum, radiation, traction in 1/6 g  (always) |
+---------------------------------------------------------------------------------+
```

- A layer that waits for a later task is listed, greyed out, with "available after T46" (for example). It is never hidden.
- "Multidimensional" stays disabled, with its reason, until two non-redundant dimensions exist.

## Coverage overlay (David, 19/11/2026)

A separate layer, **on by default and switchable off**, drawn above any value layer. It shows where our statements are weak or impossible, so that a user sees what we cover before reading any result. The value layer stays visible underneath (hatching, not a fill).

| Overlay class | Meaning | Pattern |
|---|---|---|
| No data | No elevation in the source (sea, DEM void) or outside the product (for example south of 60°S for WorldCover) | dense pastel hatching |
| Ground hidden | Forest, cropland, buildings, water, wetland, mangroves, snow or ice cover half the windows (WorldCover; rock outcrops south of 60°S) | pastel hatching, other angle |
| Screened out | Not refined at the planetary pixel: no window near any target at 90 m (T22 rule) | grey dots |
| Partial | Fewer than half the windows of the cell are valid | light hatching |
| Low confidence | Under 10 valid windows, or more than 10% of the cell masked or of unknown cover | thin outline |
| Not comparable | The selected lunar target has no Earth equivalent at its scale (for example 5 m windows) | message over the whole map |

- Each class has a text label in the legend and on hover, not only a pattern.
- The legend gives the share of land in each class for the selected scenario and target (from the run report).
- The overlay never hides a result: it qualifies it.

## Data and method panel

Opened from the overlay legend (i), from a cell and from a zone card. It answers "on what is this based?" in three short blocks:

```
+-----------------------------------------------------------------+
| WHAT WE COVER        land evaluated X%, hidden Y%, ...   (map) |
+-----------------------------------------------------------------+
| SOURCES USED HERE    Copernicus DEM GLO-30   verified <date>    |
|                      ESA WorldCover 2021     verified <date>    |
|                      LOLA LDEM_85S_40M       verified <date>    |
|                      each with licence, coverage, resolution,   |
|                      uncertainty and limits (from the catalogue) |
+-----------------------------------------------------------------+
| HOW WE PROCESSED IT  1 km windows at the lunar pixel (40 m),    |
|                      masks (7 classes), typicality against the  |
|                      lunar windows, 5 km cells, protocol v2,    |
|                      run-001; links to the method pages         |
+-----------------------------------------------------------------+
| WHAT IT CANNOT SAY   gravity, vacuum, regolith mechanics ...    |
+-----------------------------------------------------------------+
```

- Placeholders (X%, <date>) are filled from the run report and the catalogues; nothing is typed by hand.
- Every source listed comes from `data/catalog/*.yaml`, with its status. An unverified source is shown as such, never hidden.
- The processing block is generated from the run manifest (scales, masks, parameters, protocol version), not written by hand.

## Hover on a cell

```
+-------------------------------------------+
| Cell 41.73N 121.51W  (5 km, equal-area)   |
| Topography  0.64  IQR 0.48-0.77  n=24/25  |
| Geology     missing: GLiM has no unit     |  <- partial: listed by name
| State: PARTIAL (1 of 2 criteria missing)  |
| Masks: none          Confidence: medium   |
| Coverage: evaluated (24 of 25 windows)    |
+-------------------------------------------+
```

## Zone card

```
+-----------------------------------------------------------------+
| Zone 12  (9 cells, 225 km2)        Confidence: medium (MC 82%)  |
+-----------------------------------------------------------------+
| Dimension    median  IQR        >0.5   n     source             |
| Topography   0.81    0.66-0.90  78%    214   Copernicus GLO-30  |
| Geology      --      missing                 GLiM (no unit)     |
+-----------------------------------------------------------------+
| Requirements                                                    |
|  pass  Slope <= 25 deg on half the window   NTRS 20250011301    |
|  open  VIPER 15 deg                         expert decision E1  |
+-----------------------------------------------------------------+
| Strength: slope distribution.  Weakness: geology not evaluated. |
| Earth cannot reproduce: gravity, vacuum, regolith mechanics ... |
| [provenance]  [compare]  [zone vs reference]                    |
+-----------------------------------------------------------------+
```

## Comparison (2 to 4 zones)

```
             zone 12        zone 4         zone 31
Topography   |--o--|        |-o---|        |---o-|      strip plot of window typicality
Geology      missing        |--o-|         missing
LRV 25 deg   pass           pass           fail
Confidence   medium         high           low
```

## Zone against the reference

A quantile–quantile plot per parameter:
- x: planetary windows of the environment; y: zone windows;
- the 1:1 line;
- the planetary p5 to p95 band shaded.

## Validity and freshness (ADR-009)

Shown on every layer, zone card and provenance panel, from `GET /api/v3/status`:

```
+-----------------------------------------------------------------+
| Validated  protocol v1 · release r-3f2a · published 18/11       |
| Up to date  Copernicus DEM, acquired 2011-2015, file 05/2022    |
|             last check 3 h ago: no change · next in 4 days      |
+-----------------------------------------------------------------+
| Newer data  ERA5-Land detected 18/11 · recomputing compare 40%  |
|             about 2 h left · you are viewing release r-3f2a     |
+-----------------------------------------------------------------+
```

States: up to date, update in progress, update held, check failed, check overdue, not checkable, newer release published. Each has text, not only a colour.

## Provenance panel

```
slope_mean = 9.4 deg (median of 24 windows)
  product   Copernicus DEM GLO-30, tile N41_00_W122, SHA-256 1a2b...
  catalogue copernicus-dem-glo30, verified 2026-11-17
  step      resampled to 40 m (LAEA), 1 km windows, tools/... @ <commit>
  run       <run id>, parameters <link>
  compared  moon-polar-lit-highlands (LDEM_85S_40M, SHA-256 1609e9b8...)
  freshness up to date, checked 18/11 06:00 (S3 ETag unchanged)
```

## Accessibility

- **States differ by pattern, not only by colour:** hatching, dots and outline. The colour scale is cividis, colour-blind safe and perceptually uniform.
- **Text contrast** is at least 4.5:1 on `--panel`. Hatching keeps the underlying value readable on hover.
- **Keyboard:** layers, zones and comparison are reachable by Tab. Map cells are reachable through the zone list and a search by coordinates.
- **Screen readers:** each zone card is plain text; the map has a text alternative (the zone list with values).
- **Phone:** the side panel becomes a bottom sheet, and the "cannot reproduce" line stays visible.
