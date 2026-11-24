# Revisions after the v3 delivery (recorded 24/11/2026, G5 signed by David)

David's order: finish the delivery (T50), then redo the interface (T45c), then run the correspondence studies. Each line names where it comes from. Data sources still go to [data-improvements.md](data-improvements.md).

## 1. Interface (T45c, next after T50)
- **Whole-site Moon and Mars modes,** not a fifth card: background, scenarios, missions, map, texts and credits (David, 23/11).
- **3D comparison tile:** the Earth analog next to its planetary reference at the same scale, for one or several chosen constraints.
- **"Why this place":** what was compared and what was not, readable at once.
- **Figures from the release, never typed.** The home banner still shows the v2 figures (37 sites, 26 parameters, 8 sources, 71,731 LOLA windows).
- **Coherence check:** a test fails when a shown figure drifts. Every change is checked on both bodies and both languages.

## 2. Correspondence studies (after the interface)
- **E10:** an independent list of expected analogs and negative controls. It is the only way to raise external validation above 1 of 3.
- **E17:** review the lunar geology crosswalk (delegated to Claude on 20/11).
- **E20:** review the Mars volcanic crosswalk.
- **E1:** verify the VIPER climbing limit.
- **R5:** the Tanaka 2014 Mars map (David downloads it in a browser). It brings the volcanic plains target and the only positive controls of scenario D.
- **R9:** SWIM 2.0, which supersedes the 2019 ice-consistency products. It needs a protocol mars-v3, decided before any rerun.
- **Scenario C (instruments):** no run yet, and its requirements are open (E15).

## 3. Method (each one a new protocol version, decided before any run)
- **Masks:** the same tree-cover negative point fails in both releases (hidden share 0.41 and 0.37, under the 0.5 rule).
- **DEM dependence:** NASADEM keeps only 35 to 45% of the top 20. Show it per zone, or combine sources.
- **Lunar Monte Carlo noise:** still the 0.5° set for 1 km windows. Derive it from the DEM error per scale, as mars-v2 did.
- **Spatially correlated DEM errors** are not modelled.
- **Lunar pits:** self-consistency fails (KS 0.056).
- **Slope alone barely discriminates** (35 to 44% of high-confidence Mars cells reach τ 0.5).

## 4. Refresh (T52 follow-ups)
- **Recompute command:** only on David's decision, from the pre-analysis (T52b). The zone rule for publication is fixed then (proposal: hold when a zone changes by more than 10% of its cells).
- **Watch targets** for the 5 sources not checkable today: SLDEM2015, LOLA illumination, LROC pits atlas, Macrostrat, MOLA MEGDR.
- **Calibration of the Earth context step,** which the pre-analysis shows as "not measured".
- **Azure (after the NASA evaluation, David's decision):** machine prices, to turn the CPU estimates into costs.

## 5. Data access
- **D1:** an Earthdata account (MODIS thermal cycling, EMIT mineralogy).
- **R7:** Mars Climate Database registration.
