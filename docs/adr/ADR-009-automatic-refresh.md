# ADR-009 Automatic refresh, incremental recompute, freshness shown to users

Status: proposed (T30, 18 November 2026), for gate G3. Implements David's decision of 18 November 2026: refresh is automatic, only what changed is recomputed, and every user sees how old the data are, whether they are valid, and whether a newer version is being computed.

## 1. Watching the sources
A `refresher` checks every source used by a `keep` or `context` parameter, or by a site set, on its own schedule. It reads a machine signal; it never assumes that a source changed or did not change.

| Family (catalogue ids) | Signal compared with the last ingest | Published cadence, as read on 18/11/2026 | Check |
|---|---|---|---|
| Copernicus DEM on AWS (`copernicus-dem-glo30`, `-glo90`) | S3 listing (ETag, size, LastModified) and `tileList.txt` | File names carry no release code ([readme](https://copernicus-dem-30m.s3.amazonaws.com/readme.html)). ESA lists releases 2021_1 to 2024_1, about one a year: from a search excerpt, **not verified** on the page | weekly |
| NASA Earthdata through CMR (`modis-mod11a2`, `modis-mcd19a2-aod`, `emit-l2b-minerals`, `aster-ged-ag100`) | Collection `updated_since`, granule `revision_date` | MOD11A2: 8-day composites (catalogue). Others **not verified** | daily |
| Copernicus CDS (`era5-land`, `era5-single-levels`) | Dataset update date, and the months of the period fixed in the spec | ERA5-Land monthly means: "monthly with a delay of 2-3 months". ERA5: "updated daily with a latency of about 5 days"; the preliminary ERA5T may differ from the final release 2 to 3 months later ([CDS](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means)) | weekly |
| NASA PDS (LRO, MRO, MGS, Odyssey, Lunar Prospector, OMEGA products) | ETag, Last-Modified and checksum of the exact files used, plus the node's release table | LRO: "most LRO instrument teams release data every three months". Release 67 came out on 15/09/2026, and release 68 is planned for 15/12/2026 ([PDS Geosciences](https://pds-geosciences.wustl.edu/missions/lro/)). MRO: quarterly, HiRISE monthly. Notifications are by email only, with no feed, so the refresher polls | weekly; daily in the week after a planned release |
| Publications and live services (`glim`, `obu-permafrost-2018`, USGS geologic maps, `swim-ice-consistency`, `lmd-mars-climate-database`, `macrostrat`, `earthscope-mustang-noise`, site sets) | DOI or landing-page version where one is machine-readable | **Not verified** | monthly, or state `not_checkable` |

- **ERA5 rule:** only consolidated months inside the period fixed by the spec are used. ERA5T is never used. A new month outside the period is logged as "not used" and triggers no recompute.
- **Cadences in the catalogue:** T52 records each cadence in `data/catalog/*.yaml` (`refresh:` block with signal, cadence, interval and verified URL). A cadence that cannot be read at its source stays "not verified", and only the check interval depends on it.

## 2. Recomputing only what changed
Each step output has a key: `sha256(input keys + step code commit + parameters)`. Before running a step, the planner compares the new keys with those of the current release. It reruns a unit only when its key changed, and reuses the stored output otherwise.

| Change detected | What reruns |
|---|---|
| Earth source objects (tiles, granules) | `features` for the 1° tiles they cover, `compare` for those cells, `zones` for the zones that touch them (one cell of margin), and `export` for the map tiles that cover them and their parent tiles |
| A planetary source | Its profile, then `compare` for the environments that use it, reusing the stored Earth features, then `zones` and `export` for those layers |
| A spec, parameter, scenario or step code | Everything downstream of the step that reads it |
| Nothing | Nothing. The check is still recorded with its time |

- **Global steps:** a step whose result depends on all cells declares `scope: global` and always reruns fully. This applies to `validate` (all controls and the regression anchor) and to the screening top-10% of ADR-007.
- **Withdrawn tile or granule:** its cells become `not_evaluated` with the reason "withdrawn by the source", never a value.
- **Dry run:** the planner prints the plan (units per step, estimated time from the measured step times) before running. A test checks that a one-tile change reruns exactly that tile's units.

## 3. Publishing
- **Staging:** the new release is built in staging. Unchanged files are shared by hash, not copied.
- **Automatic publication**, only if:
  - the validation protocol (`validation-protocol-v1`) passes;
  - the regression anchor holds (71,731 windows, tolerance 0.01);
  - less than **1%** of evaluated cells change state and no zone appears or disappears. This threshold is proposed, not measured, and is calibrated in T52.
- **Switch:** when those conditions hold, `releases/current` switches atomically. The last 3 releases stay readable, so a cited release id keeps working.
- **Otherwise the release is held:** David sees why and approves or rejects it with `tools/discovery/release.py approve|reject <id>`.

## 4. What the user sees
The refresher writes `status.json`, served by `GET /api/v3/status`. Each layer, zone card and provenance panel shows two independent indicators:

- **Validity:** "Validated (protocol v1, release `<id>`, published DD/MM)", or "Not validated".
- **Freshness**, one of:

| State | Example of what the user reads |
|---|---|
| `up_to_date` | "Copernicus DEM, acquired 2011 to 2015, file dated 05/2022. Last check 3 h ago: no change." |
| `update_in_progress` | "A newer ERA5-Land version was detected on 18/11. Recomputing: compare 40%, about 2 h left. You are viewing release `<id>`." |
| `update_held` | "A newer version has been computed and is waiting for review: validation failed, or 3% of cells change." |
| `check_failed` | "Source unreachable since 18/11 09:00. Last successful check on 17/11." |
| `check_overdue` | "Not checked since 02/11." This appears when the last check is older than twice its interval, for example because the refresher is stopped. |
| `not_checkable` | "No automatic signal. Checked by hand on DD/MM." |
| `newer_release` | Shown when the user has an older release open: "A newer release is published. Show it." |

The data date is the source's own date (acquisition period and file or version date), never the ingest date alone.

## 5. Where it runs
- **Container:** a `refresher` service in `docker-compose.yml`, Python, using `tools/discovery`. It is the only container with outbound network, restricted in code to the catalogue hosts. It is also the only one with write access to `C:\Users\david\earthmoon-data\`. The API and `apps/discovery` stay read-only and offline (ADR-005).
- **Local only:** nothing runs in Azure (ADR-008). When Docker is stopped, nothing is checked, and the interface says so (`check_overdue`).
- **Credentials:** the CDS key and the Earthdata login are read from a local, uncommitted env file and never logged.

## Rejected
- **Recompute everything on every change:** 26,450 tiles, hours of CPU for a one-tile change.
- **A refresh button for users:** it would give a public route network and write access, and let anyone start hours of downloads.
- **Fetching live sources during a request:** it breaks reproducibility (ADR-003).
