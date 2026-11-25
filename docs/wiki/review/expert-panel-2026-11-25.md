# Simulated expert panel, 25/11/2026: detailed reviews

**Read this first.** These five reviews were written by AI reviewers, each given the role of an expert. **They are not opinions of real people.** They are a structured self-review to prepare the questions for real experts ([plan](../../plan/review-2026-11-25.md), phase E). Each reviewer read the repository and searched the web. Sources they found are listed with their links. Anything marked "not verified" was not checked against a full text.

Roles: lunar planetary geologist, Mars analog scientist, instrument test and calibration engineer, analog campaign manager (the customer), market and methods analyst.

## 1. Lunar planetary geologist
- **Good:**
  - never over-claims;
  - same pixel on both bodies;
  - targets are distributions, not intervals around famous places;
  - honest redundancy test (8 metrics, one independent property);
  - careful geology crosswalk ("unresolved" is not "no match").
- **Main criticism: slope at 1 km is the wrong primary criterion, except for mobility.** Real lunar selections rank on:
  - **material:** lithology, impact melt, glass;
  - **process:** impact, basaltic volcanism, cold traps;
  - **surface condition:** bare ground, albedo;
  - **practicality:** access, permits, prior datasets.

  Our own run-002 shows it: 36 of the 40 top dossiers are forested or farmed hills, and 0 of 40 match on lithology.
- **Scale:**
  - analog value lies at 1 to 100 m;
  - 5 km cells and the 3-cell rule filter out Haughton, Mistastin, pits and lava tubes.
- **Validation:** testing controls on slope, a dimension that cannot detect them, is uninformative. Score each control on the dimension its reference justifies (Mistastin on geology).
- **Scenarios:** normalise into use-case presets. Scenario C already shows the way.
- **Top improvements:**
  1. independent analog gazetteer (USGS, ESA/Open University) as controls and overlay;
  2. impact-structure layer;
  3. use-case presets with per-dimension controls;
  4. surface-material proxy at 100 m (ASTER GED, EMIT);
  5. Diviner rock abundance as classes;
  6. a bare-ground filter and 30 m windows.
- **Sources:**
  - [NASA Artemis field-geology training sites](https://www.nasa.gov/missions/artemis/nasa-field-geology-training-prepares-artemis-mission-support-teams/)
  - [USGS Known Terrestrial Analog Sites](https://www.usgs.gov/data/known-terrestrial-analog-sites-planetary-science)
  - [ASTER GED](https://catalog.data.gov/dataset/aster-global-emissivity-dataset-100-meter-hdf5-v003)
  - [Hayne et al. 2017, Diviner](https://arxiv.org/pdf/1711.00977)
  - [NTRS lunar analogs](https://ntrs.nasa.gov/api/citations/20100033667/downloads/20100033667.pdf)
  - Not verified: the licence of the Earth Impact Database, and Lanzarote's role in ESA training.

## 2. Mars analog scientist
- **Good:**
  - unfavourable results first;
  - protocol frozen before the run, with an auditable control rule;
  - Martian data only, with Monte Carlo noise measured from the DEM error;
  - observed-share screen.
- **Criterion:** km-scale slope is a weak geomorphic filter. Mars analog selection is **functional**: chemistry, aqueous minerals, ice, preservation, climate.
  - [Foucher et al. 2021](https://hal.archives-ouvertes.fr/hal-03130725)
  - [Preston & Dartnell 2014](https://ui.adsabs.harvard.edu/abs/2014IJAsB..13...81P)
- **Why run-mars-002 fails: mostly the choice of controls, then scale.**
  - The R29 sites come from [NASA BASALT](https://www.nasa.gov/ames/basalt), chosen for basalt astrobiology and spacewalk operations.
  - Their relief is shield flanks, caldera walls and cinder cones.
  - R29 justifies the **geology** dimension, and geology passes at all 4 controls.
- **Sound validation:**
  - controls matched to the dimension: for plains slope, the Snake River Plain low shields ([Hauber et al. 2009](https://ui.adsabs.harvard.edu/abs/2009JVGR..185...69H/abstract)) and the Laki and Búrfells lavas ([Keszthelyi et al. 2004](https://pubs.usgs.gov/publication/70200837));
  - a discrimination test (AUC);
  - an independent list;
  - a matched scale.
- **Coherence:**
  - scenario C already lists Martian targets, but the Mars mission has no instrument axis;
  - proposed presets: sample caching and astrobiology, drilling and ice, GPR, spectroscopy, mobility, ISRU, basaltic geology.
- **Top improvements:**
  1. split the plains from the edifices, and restate R29 as geology controls;
  2. a discrimination test;
  3. an aqueous-minerals target ([MOCAAS](https://www.ias.u-psud.fr/moccas/) against [GLiM](https://doi.pangaea.de/10.1594/PANGAEA.788537));
  4. presets;
  5. multi-scale relief;
  6. dust cover and thermal inertia as Mars context ([TES dust cover index](https://www.mars.asu.edu/data/tes_ruffdust)).

## 3. Instrument test and calibration engineer
- **Good:** honesty. The data model already gives Mars targets to the instruments (C1, C3, C4, C5, C6), so **the Moon/Mars imbalance is mostly in the interface**.
- **Not good:**
  - **The Moon "Instrument calibration" mission still uses the v2 framing.** Its texts say "dry, calm, cold" and include a seismometer, which is comfort scoring rejected by K2. The seismometer is not in scenario C.
  - Scenario C was never run.
  - Every instrument requirement is open (E15).
  - Scale: we screen regions; we cannot qualify a test site.
- **What each instrument family needs from a site:**
  - **GPR:** dry or frozen ground with known layers;
  - **spectrometers:** fresh outcrops with laboratory ground truth;
  - **lidar and navigation:** slope and roughness. A low polar Sun cannot be had on Earth: the Canadian Space Agency used an 18 kW lamp;
  - **thermal:** homogeneous surface with clear skies (RadCalNet sites);
  - **drills:** ice-cemented ground;
  - **mobility:** slope plus soil type;
  - **all families:** access, permits, season.
- **Model:** normalise. **The preset is keyed on the use case (the test objective), not on the hardware.**
  - A preset chooses targets, gates (met, failed or unknown), context, scale and outputs.
  - It never re-weights similarity.
  - Thresholds are set per body.
  - Prior campaigns appear as cited annotations, never as filters.
- **Top improvements:**
  1. replace the calibration mission with shared presets;
  2. presets that drive the rules;
  3. a test-site dossier;
  4. logistics and permits;
  5. exact Sun elevation and cloud cover;
  6. homogeneity at the instrument footprint.
- **Sources:**
  - [WISDOM tests](https://pmc.ncbi.nlm.nih.gov/articles/PMC5568567)
  - [Martin et al. 2020](https://resolver.caltech.edu/CaltechAUTHORS:20200131-152046441)
  - [CSA lidar test](https://arxiv.org/pdf/2601.03371)
  - [IceBreaker](https://astrobiology.nasa.gov/news/icebreaking-mars/)
  - [RadCalNet](https://storymaps.arcgis.com/stories/ddeb90ab01a24e42a32f16a281ed8575)

## 4. Analog campaign manager (the customer)
- **Use today:** as a scouting aid only.
  - **Good:** honest, global, requirements kept apart, frozen releases.
  - **Blocks:** ranks on slope only; half the land is masked; top zones are fragile to a change of DEM.
  - **The interface says more than the documentation**, for example "we rank real Earth sites" and "a lunar base needs ice and polar light".
- **The real decision is "where can my team run test X, in window Y, safely, legally, within budget".** Terrain is one input out of about twelve. Missing inputs:
  - access and logistics: logistics take 50 to 75% of a remote campaign's effort ([NTRS](https://ntrs.nasa.gov/api/citations/20140003548/downloads/20140003548.pdf));
  - permits and protected areas;
  - Indigenous land and consultation;
  - seasons;
  - safety;
  - prior campaigns and infrastructure;
  - cost class;
  - environmental impact;
  - characterisation data at test scale.
- **Outputs expected:**
  - a one-line verdict per card, with a go/no-go checklist that says "not assessed" where it applies;
  - a site dossier (PDF or Markdown);
  - a comparison of 2 to 5 sites, benchmarked against a known site;
  - GeoJSON and CSV exports with the release id;
  - a stable API.
- **Who to involve:**
  - analog campaign managers (NASA, ESA, CSA);
  - external analog researchers, for the independent list;
  - landing-site and geology teams, for the crosswalks;
  - rover mobility engineers;
  - instrument principal investigators (PIs);
  - commercial lander companies;
  - permit, environment and Indigenous-relations advisers;
  - field safety officers.
- **Top improvements:**
  1. a benchmark against known analogs ([ESA/Open University catalogue](https://www.esa.int/Our_Activities/Preparing_for_the_Future/Discovery_and_Preparation/Cataloguing_otherworldly_landscapes_on_Earth));
  2. an access and constraints layer, as context;
  3. a site dossier and exports;
  4. interface texts aligned with v3;
  5. the workable season per zone;
  6. links to fine-scale data.

## 5. Market and methods analyst
- **Market:** an academic and agency niche, not a commercial market. No global, quantitative, reproducible screening tool covering both bodies was found, so the gap is real. Existing work:
  - [USGS Known Terrestrial Analog Sites](https://catalog.data.gov/dataset/known-terrestrial-analog-sites-for-planetary-science): a point layer;
  - the ESA/Open University catalogue: logistics, permits and contacts, as a PDF;
  - [Europlanet field analogues](https://europlanet-society.org/?p=8693);
  - the PTAL spectral library ([arXiv](https://arxiv.org/pdf/2101.08305));
  - geomorphon pattern search ([Jasiewicz & Stepinski](https://www.geomorphometry.org/uploads/pdf/pdf2013/Jasiewicz2013geomorphometry.pdf));
  - MOLA roughness at several baselines ([Kreslavsky & Head](https://www.mars.asu.edu/data/mola_roughness)).
- **Our differentiators:**
  - every land cell is assessed;
  - Earth is compared at the planetary pixel;
  - four data states;
  - frozen protocols;
  - Monte Carlo;
  - hashes and provenance;
  - an open API.
- **Our weaknesses:**
  - one property compared;
  - external validation 1 of 3;
  - no logistics, materials or rover scale.
- **Methods:**
  - **MOLA interpolation smooths Martian slopes, while the Earth DEM is fully sampled,** so Earth looks too steep. Degrade Earth along synthetic MOLA tracks, or use MOLA-HRSC.
  - **The two-sided percentile scores closeness to the median, not membership:** a value at the 92nd percentile is still a normal Martian value. Alternatives: membership of the central 90%, a density score on log(slope), or a distribution distance per cell.
  - **Ranking zones across targets is biased:** one window per cell gives extreme medians. Rank within each target, or on a lower bound.
  - **Controls:** use polygons, state the scale at which a control is claimed to be an analog, and give a bootstrap interval with 4 controls.
  - **"Never combined":** keep it, but give a shortlist through a Pareto front (no weights) and explicit user presets labelled "user choice, not a score".

## Checked tonight against our data
- **Hypothesis (Mars scientist):** the steep tail of the volcanic profile comes from the edifices.
  - Result ([data](../../../data/runs/run-mars-002/profile-tail-by-unit.json)): edifices are 5% of the windows but 26% of the tail above the 89th percentile (2.48°).
  - Conclusion: they are over-represented, but 74% of the tail is plains units. **Partly true.**
