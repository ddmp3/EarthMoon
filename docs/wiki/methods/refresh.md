# Refresh: sources watched, local recompute, provenance (T52, ADR-009)

**Status:** detection, planning, publication rules, freshness, provenance and local zones are done (T52). The refresher checks and identifies but **never starts a recompute** (David, 24/11/2026): every detected change gets a pre-analysis of its volume (T52b), and a recompute is decided from it. On Azure each recompute will have a cost.

## What is watched
Every source a release names (16 on 23/11/2026) has a `refresh` block in `data/catalog/*.yaml`:
- **The signal:** an S3 listing, the size and date of a file, a version on a page, a DOI version, or an API value.
- **The check interval.**
- **The publication cadence:** quoted from the source page, or "not verified".

First real check (23/11/2026):

| Result | Sources |
|---|---|
| Signal recorded | Copernicus GLO-30 and GLO-90 (26,450 and 26,475 tiles), WorldCover (2,651 tiles), aridity, permafrost, rock outcrop, Natural Earth, Lunar Prospector, SWIM |
| Same size as the ingest | LOLA 85°S 40 m, USGS lunar geologic map |
| Not checkable: no target recorded at ingest | SLDEM2015, LOLA illumination, LROC pits atlas, Macrostrat, MOLA MEGDR |

Rules:
- An unreachable source is `check_failed`, never "up to date".
- A source with no signal is `not_checkable`.
- A check older than twice its interval is `check_overdue`, so a stopped refresher shows.
- The refresher runs in its own container (compose profile `refresh`, no port, outbound to catalogue hosts only), and is the only writer of the data folder.

## New planetary data
The refresher also reads release tables. It starts with LRO: "Release N of LRO data is now online".
- **A new entry** is logged "detected, to verify", with its date, in the status.
- **It is never used in a run.** A new reference (a new region or a finer product) is a new protocol version, decided before any run.

## Pre-analysis of an update (no compute)
For each detected change the refresher estimates, from the served releases and without any heavy step (`tools/discovery/impact.py`):
- what changed: the source, its files, and the 1° tiles they cover;
- what would be recomputed: tiles reassessed with their neighbours, targets, estimated cells;
- the estimated CPU time, from the calibration below. A step that was never calibrated (the Earth context) says "not measured", never 0.

Examples on the served releases (24/11/2026):

| Change | Would recompute | Estimated CPU |
|---|---|---|
| One Copernicus GLO-90 tile | 9 tiles for Moon and Mars (about 4,400 cells) | 12 s |
| LOLA 85°S file | 3 lunar targets on 24,436 tiles (6.3 M cells), no Earth feature | 0.38 h |
| MOLA MEGDR files | 3 Martian targets on 32,138 tiles (7.4 M cells) | 0.50 h |
| Permafrost model | Earth context layer only | not measured |

It is shown in the status of the website ("1 update detected, not recomputed: …"). The pre-analysis is built so a cost can be added from machine prices.

## Recompute: only what changed
Each unit has a key: its inputs, its code version and its parameters (`tools/discovery/refresh_plan.py`).

| Change | What reruns |
|---|---|
| One Earth tile | That tile's features, the cells of the tile and of its neighbours, the zones that touch changed cells, their Monte Carlo, the cheap checks, the affected exports |
| One planetary source | Its target's profile and its target only, on every tile; no Earth feature |
| Code or a parameter | Everything downstream |
| Nothing | Nothing |

**Zones** are updated locally (`tools/discovery/zones_local.py`):
- The update starts from the changed cells and walks only their candidate neighbours, to the edge of each zone touched.
- Tests show the result equals a full recomputation.

## Publication
A refreshed release is published only if all of these hold:
- the validation protocol passes;
- the regression anchor holds (lunar: 71,731 windows within 1%; Mars has none);
- under 1% of evaluated cells change state;
- no zone appears or disappears.

Otherwise it is held with its reasons. Approve it or reject it with `python -m discovery.publish approve|reject <id>`.

Every Moon and Mars release today is "not validated" (positive controls and masks), so a refreshed release waits for review.

## Calibration (23/11/2026, 10 Mars tiles, no download)
The simulated update re-read 10 tiles with an elevation error within the stated Copernicus accuracy (sigma 1.216 m). This is a re-release that changes nothing real. The rule was written before running.

Time per step:

| Step | Time |
|---|---|
| 10 tiles recomputed at both scales | 18 s |
| 89 tiles reassessed (18,636 cells) | 5 s |
| Zones of 3 targets, updated locally | 2.3 s (9 to 17 cells walked) |

What changed:
- **Coverage state:** 0 cells.
- **Candidacy:** 2 cells of 18,636, at the poles.
- **Zones:** one polar zone gained or lost one cell.

Consequences:
- The **1% threshold is kept**.
- The **zone rule needs a decision**: a zone that changes by one cell counts as one zone out and one in, so even this no-change re-release would be held. A rule based on the share of a zone's cells goes to David.

Data: `data/runs/t52-calibration.json`.

## Provenance for researchers
**For each Earth tile**, every release from T52 on publishes `provenance.json`:
- the source files read, with their version (ETag, size, SHA-256) and date at the source;
- when the tile was computed (not recorded before T52, and said so);
- the code version and commit;
- the release where the tile last changed.

**For each release**, `changes.json` gives:
- the previous release;
- the source events;
- the tiles recomputed, added or withdrawn;
- the source files whose version changed;
- the publication decision and its reasons.

**Access:**
- API: `GET /api/v3/tiles/{lat,lon}/provenance` and `GET /api/v3/changes`.
- Website: the site panel lists the tile's sources with their file dates, the computation date and the release where it last changed.
