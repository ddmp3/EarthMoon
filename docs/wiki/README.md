# EarthMoon wiki (source)

Long-form material that the short docs in `docs/` summarize: data inventories, method experiments, run reports, history. This folder is the source of truth; the GitHub wiki is a mirror built by `python tools/docs/publish_wiki.py`. Do not edit the GitHub wiki by hand.

| Folder | Content | Written by |
|---|---|---|
| `data/` | Lunar ([moon.md](data/moon.md)), Martian ([mars.md](data/mars.md)) and Earth ([earth.md](data/earth.md)) data inventories; [coverage review](data/coverage-review.md) | T10, T11, T12, T14 |
| `methods/` | Environment profiles ([profiles.md](methods/profiles.md)), [parameters](methods/parameters.md), [sampling](methods/sampling.md), [comparison](methods/comparison.md), [mapping](methods/mapping.md), sampling, comparison, mapping | T20 to T26 |
| `runs/` | Reports of computation runs, with hashes and numbers: [earth cube](runs/earth-cube.md), [lunar profiles](runs/moon-profiles.md), [comparison pilot](runs/compare-pilot.md), [run-001](runs/run-001.md), [run-002](runs/run-002.md), [run-002 geology](runs/run-002-geology.md), [run-002 context](runs/run-002-context.md) | T40 onwards |
| `ui/` | Interface specifications ([map-spec.md](ui/map-spec.md)) | T26 |
| `v2/` | Full v2 scientific documents, unchanged | T02 |
| `baseline.md` | Quality baseline before v3 | T01 |
| `rankings.md` | Latest rankings report of the running API (`tools/validation/rankings.py`) | v2 |
