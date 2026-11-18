# Earth feature cube, topography (T40 run, 18/11/2026)

Global screening stage at 90 m and fine stage at 40 m on 113 tiles: the 13 T22 pilots plus 100 random tiles (seed 20261120). Computed locally with Docker; nothing on Azure.

## Versions and hashes

| Item | Value |
|---|---|
| Code version (`code_version()`, sha256 of the cube sources) | `48f0769636913b581cba2a1253885b3da206dc29b7bd087f3beaa6084feda220` |
| Commits (provenance) | 90 m: `c979668`; 40 m: `04d8a65` (same code version) |
| Image and libraries | `python:3.11.11-bookworm`, numpy 2.4.6, rasterio 1.4.4 (GDAL 3.10.3), pyarrow 26.0.1 |
| Manifest 90 m (`glo90-90m/manifest.jsonl`) | sha256 `05989cdc49ef8de2384322e61f6a664bb0f1f66cde2f34ab2ff2631ee1fec692` |
| Manifest 40 m (`glo30-40m/manifest.jsonl`) | sha256 `114f04cd16424206356a02d0cfda77335cd495f41bbd4d7dadf7ef535b229bd8` |
| GLO-90 listing (`glo90-90m/listing.json`) | sha256 `fd0075fd75dde4dfca1f58fb42077438934e666650f37d308abb16f484b7fd5c` |
| GLO-30 listing (`glo30-40m/listing.json`) | sha256 `bc542f2240595cdf6574b278675d3d7e743e9905f192aa2a8e12cd0d52aeb39b` |
| WorldCover 2021 v200 listing | sha256 `02e5d6e9b2798f2c2d2e7c80ca3b8b288ba4343f2d563fa75260be93d37d20ac` |

Every manifest line gives, per tile: input objects with ETag, size and LastModified (plus SHA-256 for local copies), the content key, the code version, the commit, the parameters and the SHA-256 of both Parquet tables. A manifest holds every run: the last line of a tile is the current one (`measure.py summary`).

## Sources as listed on 18/11/2026

| Source | Tiles | Size | Note |
|---|---|---|---|
| Copernicus GLO-90 | 26,475 | 0.071 TB | Cached locally (67 GB): each file is a single block |
| Copernicus GLO-30 | 26,450 | 0.589 TB | Streamed (COG range reads), not stored |
| ESA WorldCover 2021 v200 | 2,651 | not summed | 60°S to 84°N only |

All Copernicus files are dated 2022-05-09. T22 had estimated 0.96 TB (GLO-30) and 0.14 TB (GLO-90) from a few tiles.

## Coverage

Cells are 5 km. Missing cells were split with WorldCover (`measure.py breakdown`).

| Stage | Cells | Evaluated | Partial | Missing | Missing: water | Missing: outside WorldCover | Missing: land |
|---|---|---|---|---|---|---|---|
| 90 m, global | 7,738,248 | 80.66% | 1.23% | 18.10% | 687,618 | 712,974 | 258 |
| 40 m, 113 tiles | 43,984 | 80.53% | 1.22% | 18.25% | 4,344 | 3,667 | 18 |

- Windows (1 km): 187.7 million at 90 m, of which 150.9 million valid (at least 90% of pixels).
- "Outside WorldCover" is mostly sea and ice shelves south of 60°S. It cannot be split further until the Antarctic outcrop mask is wired in (T43, catalogue entry `add-rock-outcrop-v7-3`).
- Missing is never filled and never scored. Partial means fewer than half the windows of the cell are valid.

## Timings

| Stage | Workers | Wall time | Per tile (median / p90) | Rate |
|---|---|---|---|---|
| 90 m, global, cached DEM, WorldCover mask | 12 | 1.05 h | 1.74 s / 2.71 s | 25,107 tiles/h |
| 40 m, 113 tiles, streamed, neighbours read, mask | 8 | 0.13 h | 27.2 s / 50.4 s (read 23.0 s, mask 2.4 s) | 903 tiles/h |

**ADR-007 stop rule:** a global 40 m run would take about 26,450 / 903 = 29 h at the measured rate (24.9 h from the median tile time). That is under 72 h, so the rule is not triggered. Reading GLO-30 dominates (85% of the tile time).

Outputs: 5.4 GB for the global 90 m cube, 37 MB for the 113 tiles at 40 m.

## Checks

- **v2 anchor:** the v3 code reproduces every value and sigma of the 37 v2 sites within 0.0015 (`test_anchor_v2.py`).
- **GLO-90 against GLO-30 resampled to 90 m** (13 pilot tiles, 119,307 windows): median slope ratio 0.978, Spearman 0.9997, absolute difference median 0.057°, p95 0.579°. GLO-90 can serve as the screening layer.
- **Rebuild:** same inputs give byte-identical Parquet (test). The 40 m rerun with the final code gave the same cell counts as the first run.
- **Unit tests:** `tools/discovery` (analytic plane, bowl, noise, holes, tile ownership, keys, masks).

## Corrections made during the run

1. The recorded commit was read inside the container for every tile: it changed when a commit landed mid-run, and the Windows mount marked it dirty. It is now read once on the host.
2. Pixels without WorldCover were counted as "not ice, not water": Antarctica had an ice fraction of 0. They are now unknown, and `wc_covered` gives the covered share. The catalogue entry of WorldCover now says 60°S to 84°N.

## Limits

- No water or ice mask south of 60°S yet (27% of GLO-90 tiles): flagged by `wc_covered = 0`.
- How ESA built the WorldCover overviews read at 90 m and 40 m is not stated in the files: not verified.
- Copernicus is a surface model: forest and buildings add slope. FABDEM (catalogue, T14) can check candidates.
- GLO-30 is identified by ETag only (streamed, no SHA-256 of the whole file).
