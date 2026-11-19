# Lunar profiles (T41 run, 18/11/2026)

Every lunar environment of T20 is computed from primary data with the Earth window code (`tools/discovery/windows.py`). Profiles are in `data/profiles/moon/<id>.json`: inputs with SHA-256, code version, parameters, percentiles of every metric, and sensitivity runs. Every selected window is kept in a Parquet file outside git, and its SHA-256 is in the profile.

## Profiles

`slope_mean` percentiles, in degrees:

| Profile | Source and scale | Windows | p5 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| South polar cap (v2 anchor) | LDEM_85S_40M, 1 km | 71,731 | 2.954 | 5.231 | 8.314 | 12.886 | 20.892 |
| Polar lit highlands (`f_lit` 0.05) | LDEM_85S_40M, 1 km | 58,245 | 2.95 | 5.19 | 8.33 | 12.76 | 20.28 |
| Permanently shadowed regions (`f_psr` 0.75) | LDEM_85S_40M, 1 km | 6,162 | 2.54 | 4.57 | 9.49 | 15.94 | 26.82 |
| Persistently lit (q 0.5) | 5 m mosaic, 100 m | 859 (622 valid) | 1.79 | 3.00 | 4.35 | 6.18 | 9.92 |
| Mare plains | SLDEM2015, 1 km | 5,699,377 | 1.50 | 1.88 | 2.25 | 2.97 | 6.28 |
| Fresh (Copernican) craters | SLDEM2015, 1 km | 594,862 | 2.89 | 4.84 | 7.52 | 12.20 | 25.19 |
| Degraded (pre-Nectarian, Nectarian) highlands | SLDEM2015, 1 km | 13,328,274 | 3.05 | 5.36 | 8.24 | 12.54 | 21.02 |
| Pits (site set, context window) | Atlas + SLDEM2015 | 278 pits, 271 with context | 1.57 | 2.28 | 3.70 | 6.19 | 11.74 |

- **Anchor:** the v2 reference is reproduced exactly: same 71,731 windows, same file (`1609e9b8…`), same percentiles. It is tested in CI from the committed profile, and locally from the LDEM file.
- **Lit highlands:** depends on `f_lit`. With no shadow allowed (`f_lit` 0), the median rises to 9.9° (38,735 windows): fully lit windows are ridges.
- **Shadowed regions:** stable across thresholds and window sizes; the median stays between 9.2 and 9.9°. The PSR map is read in the LDEM orientation: PSR pixels lie 215 m below their surroundings, against 13 to 39 m for the 7 other orientations (test).
- **Persistently lit:** areas lit more than 60% of the time are narrower than 200 m on the 60 m map. No 240 m square fits inside one. The spec's middle values (q 0.6, 200 m) select nothing, so the nominal falls back to q 0.5 and 100 m windows (rule in the profile).
- **Mare plains:** the mare units of the geologic map (Em, Im1, Im2, Imd) are used, as the spec planned once the map was verified (T14).
  - Iron rule (FeO split 11.44 wt%, area-weighted Otsu): 6.3 M windows, of which 4.6 M are in the map's mare units. Median 2.50°, because 15 km iron bins mix mare edges.
- **Craters and highlands:** units Cc, Ccc, Csc, and the 13 Nectarian and pre-Nectarian units. Unit-share and unit-list sensitivities move the median by less than 0.2°.
- **Pits:** 229 of 278 lie in Copernican crater units (impact melt of King, Copernicus, Tycho…) and only 15 in mare units. The atlas gives a host feature, not a setting; the map unit is given instead.
  - Not computed: NAC DTM slopes (public DTMs preliminary, post spacing not stated) and GRAIL gravity (cannot resolve one tube).

Not computed in T41: thermal, volatile and radar layers (Diviner, LAMP, Mini-RF, LEND) belong to T47; Lunar Prospector thorium belongs to T46.

## Effective resolution (finding L3)

`data/profiles/moon/effective-resolution.json`, on 31,825 windows of 1 km between 87°S and 90°S:

- **LOLA 40 m against the 5 m mosaic averaged to 40 m** (same windows, same code):
  - `slope_mean` median ratio 1.006, Spearman 0.9999, absolute difference median 0.05°;
  - percentiles within 0.1°;
  - no trend with the share of pixels that have a laser return (2 to 18%).
- **Short-wave power** (160 m against 2 km): LOLA 40 m has 1.5 to 2.3 times more than the mosaic, not less. The 5 times deficit against Earth (T22) is not a smoothing peculiar to LDEM.
- **Limit:** both products come from the same laser tracks, which hit about 6.5% of 5 m pixels. The experiment cannot tell whether the real surface has more short-wave relief. That needs independent data, such as NAC stereo DTMs.
- **Earth match:**
  - giving Copernicus the LOLA short-wave power needs a Gaussian smoothing of 1 to 1.5 pixels (40 to 60 m);
  - that smoothing lowers Earth `slope_mean` by 21 to 31% (3 to 8° terrain) and by 12% (above 8°).

**Decision for David:** keep T22 decision 1 (no smoothing, the anchor unchanged), and have T42 report the ranking with a 1-pixel smoothing as a sensitivity run. Smoothing Earth by default would rest on an unproven cause.

## Runs

| Step | Time | Note |
|---|---|---|
| Lunar window cube, SLDEM2015 60°S to 60°N | 0.16 h, 12 workers | 43,200 tiles, 32,330,880 windows, all valid; 1.8 GB |
| Cube profiles (mare, craters, highlands) | about 10 min | Reading 43,200 Parquet files through the Windows mount |
| Persistently lit, 5 m mosaic | 12 min | 3 window sizes x 3 thresholds |
| Effective resolution | about 5 min | Plus the 13 GLO-30 pilot tiles streamed |

Inputs: SLDEM2015 (32 tiles, 45.3 GB), LDEM_85S_40M, the 5 m mosaic and count map, the 60 m illumination and PSR maps, Lunar Prospector FeO (0.5°), the Unified Geologic Map v2 (`f3ec2980…`), the LROC pits list page (`f1378ee0…`). Their SHA-256 are in the profiles and in `moon-cube/inputs.json`.

Fixed during the run:
- The lunar cube first sent the 265 MB unit grid to every task: 10 h projected. Each worker now opens it once: 0.16 h.
- A list of 32 M rows built in Python ran out of memory; numpy columns are used instead.
