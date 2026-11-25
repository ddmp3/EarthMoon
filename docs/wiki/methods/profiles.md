# Planetary environment profiles (T20)

Specs: `data/profiles/spec/*.yaml`. Check: `python tools/profiles/profiles.py`. Values are computed later (T41 Moon, T48 Mars).

## Rules

- An environment is **selected from planetary data by a written rule**, never drawn around a famous place, never from Earth sites.
- A `ready` spec selects only with verified or partly verified products. A `conditional` spec names the unverified product that blocks it.
- A threshold without a value carries a **sensitivity grid**; T22 fixes it by measuring how much the profile moves.
- **No circular selection:** a variable that selects an environment is not compared afterwards.
- A profile is a **distribution** (percentiles plus every window vector, for the joint comparison of T23), or a **site set** when the data are detections.
- The candidate parameters are the v2 terrain metrics; T21 removes the redundant ones.

## Moon

| Spec | Status | Selection | Main limit |
|---|---|---|---|
| `moon-south-polar-cap-v2` | ready, **regression anchor** | All 1 km windows of LDEM_85S_40M south of 85°S (71,731 windows, SHA-256 `1609e9b8…`) | Mixes shadowed floors and lit ridges (E8) |
| `moon-polar-lit-highlands` | ready | Same windows, permanent shadow fraction ≤ f_lit | Shadow is a model built from the same terrain |
| `moon-psr` | ready | Permanent shadow fraction ≥ f_psr; window size to fix (shadowed areas below 1 km are lost) | Volatile layers are indicators; no Earth surface is dark at cryogenic temperature |
| `moon-persistently-lit` | ready | Connected areas of average illumination ≥ q; 5 m terrain (87°S to 90°S) | Illumination is modelled and not compared (it selects) |
| `moon-mare-plains` | ready | SLDEM2015 windows in the mare units of the USGS map (upgrade applied in T41); the Fe split stays as a sensitivity run | Map at 1:5,000,000 |
| `moon-pits` | ready, site set | Every pit of the LROC atlas | Atlas list not read yet; a pit is not a tube |
| `moon-fresh-craters` | ready (T41) | Copernican units of the USGS geologic map (Cc, Ccc, Csc) | Small fresh craters are not mapped at 1:5,000,000 |
| `moon-degraded-highlands` | ready (T41) | Pre-Nectarian and Nectarian units (13); mixed INp and INt left out | Unit boundaries at 1:5,000,000 |

## Mars

| Spec | Status | Selection | Main limit |
|---|---|---|---|
| `mars-ice-rich-midlatitudes` | ready | SWIM 1.0 consistency ≥ its class boundary (0 to 60°N) | SWIM is an interpretation; its component layers are excluded from comparison |
| `mars-north-polar`, `mars-south-polar` | ready | MOLA polar grid poleward of phi (75, 80 or 85°) | Labelled "polar terrain": a latitude rule mixes deposits, ice and plains |
| `mars-aqueous-mineral-sites` | ready, site set | OMEGA detection sites and CRISM footprints passing the T48 rule | Detections, not abundances; targeted |
| `mars-hirise-terrain` | ready | Every window of the 1,377 public HiRISE DTMs | Targeted sites, not a random sample of Mars |
| `mars-volcanic-plains` | ready | Volcanic units of the Tanaka 2014 map | Map downloaded by David 24/11/2026; computed in T48c (4,983 windows) |
| `mars-sedimentary-basins` | conditional | Units of the Tanaka 2014 map | Map available since T48c; unit rule not decided |
| `mars-caves` | conditional, site set | Cave candidate catalogue | Blocked: catalogue not verified |

## Rejected

Listed with reasons in `data/profiles/spec/rejected.yaml`: Mars dune fields (no catalogue; images alone would select on appearance), a whole-Moon profile (means nothing specific), lunar ice deposits as an environment (indicators only), lunar lava tubes (never observed, only pits), a continuous map of Martian aqueous minerals (detections are sites).

## Effective resolution experiment (finding L3, run in T41, decided in T22)

Question: is a 40 m LOLA polar pixel as sharp as a 30 m Copernicus pixel? LOLA polar grids are interpolated between laser tracks; Copernicus is not.

1. **Where the data are real.** The 5 m south pole mosaic ships a count map (laser returns per pixel). Aggregate it to 40 m and map, per 1 km window, the fraction of pixels with at least one return.
2. **Spectral test.** On windows with dense returns and on windows with sparse returns, compute the radially averaged power spectrum (or the variogram) of the 40 m LOLA terrain. The wavelength where the spectrum falls below the high-coverage curve is the effective resolution of that window.
3. **Earth match.** Degrade Copernicus GLO-30 by Gaussian smoothing on flat test areas chosen at random (seeded), until its spectrum matches LOLA at the same coverage level.
4. **Decision per dimension and environment (T22).** Either compare at the coarser effective scale, or degrade Earth to match, or flag windows below a coverage threshold. Topography of `moon-psr` and `moon-persistently-lit`, where windows may be smaller than 1 km, needs the 5 m mosaic and its own test.
5. **Mars.** The same test applies to MOLA polar grids (binned from tracks) against HiRISE DTMs where both exist.

Outputs: coverage map, spectra, the chosen scale and its effect on the anchor percentiles. No result is accepted if it changes the v2 anchor without saying so.

**Result (T41, [lunar profiles run](../runs/moon-profiles.md)):** LOLA 40 m and the 5 m mosaic give the same `slope_mean` (ratio 1.006); matching Earth to the LOLA spectrum would need a 40 to 60 m smoothing that lowers Earth slopes by 12 to 31%. Proposed: no smoothing by default, a 1-pixel smoothing as a T42 sensitivity run (decision for David).
