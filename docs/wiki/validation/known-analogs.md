# Known analog sites: the criteria science uses, and our protocol (T53, 25/11/2026)

**Question (David):** science has already classified sites as analogs and defined the criteria. Do our criteria and results agree with them, on a few known sites rather than the whole planet?

**How:**
- **Sites and features:** taken from an independent source, the *Catalogue of Planetary Analogues* written for ESA by the Open University (R66, 2012). It lists 15 lunar and 31 Martian features, and the Earth sites that represent each one.
- **Sites tested:** 68 points in 27 of its 30 chapters. 6 entries are excluded, each with its reason: ranges, no coordinate, or a point the catalogue contradicts.
- **Frozen first:** the rules and pass thresholds were committed before any value was read (commit d075808).
  - Rules: [criteria.yaml](../../../data/validation/known-analogs/criteria.yaml).
  - Sites: [catalogue.yaml](../../../data/validation/known-analogs/catalogue.yaml).
- **Results:** [results.json](../../../data/runs/known-analogs/results.json), with every point, its map units and its values.
- **No new global computation:** only cached data and existing run files.

## 1. What makes a site an analog, according to the literature
| Source | Criteria, in their words |
|---|---|
| Foucher et al. 2021 (R28) | "focus on the specific properties that need to be imitated": an analog is defined **by its use**. Five families: planetary landforms, processes, rocks and minerals, astrobiology, engineering. For a rover clearance test, "only their height and size" matter, not the rock |
| ESA/Open University catalogue (R66) | The analog is assigned **per feature**. The selection order is: 1) "scientific merit and relevance", 2) cost, 3) access (permits, physical access), 4) infrastructure |
| Lee et al. 2008 (R67) | Aspect of interest, application, function, fidelity, cost-effectiveness; then access, infrastructure, permits. "No place on Earth offers a high fidelity analog to all aspects" |
| Sanders et al. 2011 (R68) | Mission applicability (terrain, rock distribution, mineral, chemical and physical regolith properties), access, infrastructure |
| Morse et al. 2024 (R69) | Topography (slope, obstacles), access, **vegetation cover**, cellular signal, geologic diversity |
| Preston and Dartnell 2014 (R65) | "There are no clearly defined and followed criteria with which to evaluate them". Each site is listed with its features |

**Consensus:**
1. A site is an analog **for one feature and one use**, never in general.
2. The feature is first a **material or a landform**: basalt, anorthosite, sulphate, ground ice, impact crater, lava tube.
3. The practical criteria come next: access, permits, infrastructure, vegetation, cost.

**Our protocol does the reverse.** It ranks every place on a single relief property, slope at 1 to 11.6 km, against the whole distribution of a planetary environment.

## 2. Each criterion tested on the catalogue sites
- **Rule:** a feature is found at a chapter when one of its points has it (centre and 8 points at 1.6 km).
- **Recovered:** found at 75% or more of the chapters that list the feature and have data, with at least 3 such chapters.
- **False alarms:** among the 18 random negatives; at most 1 is allowed.
- **Land share:** the share of land cells where the strict rule holds. Above 10%, the rule is a gate, not a discriminator.

| Feature (body) | Earth rule and data | Recovered | False alarms (of 18) | Land share | Verdict |
|---|---|---|---|---|---|
| Volcanic structure (Moon) | volcanic rock, Macrostrat | 4 of 4 | 0 | 2.9% | **works** |
| Volcanic structure (Mars) | same | 5 of 6 | 0 | 2.9% | **works** |
| Pyroclastic deposits (Mars) | same | 3 of 3 | 0 | 2.9% | **works** |
| Lava flows (Mars) | same | 7 of 10 | 0 | 2.9% | just below 75% |
| Basalt (Moon) | basalt, Macrostrat | 2 of 7 | 0 | 1.5% | **fails: maps too coarse** |
| Basalt (Mars) | same | 2 of 8 | 0 | 1.5% | **fails: maps too coarse** |
| Sulphate (Mars) | gypsum or anhydrite | 1 of 6 | 0 | not computed | **fails: deposits below map scale** |
| Iron oxide (Mars) | ironstone, iron formation, laterite | 0 of 5 | 0 | not computed | **fails** |
| Carbonate (Mars) | carbonate rocks | 3 of 4 | 5 | not computed | recovered, but common: gate only |
| Clay-rich rocks, proxy for phyllosilicates (Mars) | clay, mudstone, shale... | 3 of 4 | 4 | not computed | recovered, but common: gate only |
| Ground ice (Moon water-ice; Mars polygons, icy flows) | permafrost probability ≥ 0.5 (R32) | 4 of 4 | 2 (boreal forest, wetland) | 9.1% | recovered, needs a vegetation gate |
| Present-day aridity (Mars) | aridity index < 0.2 | 2 of 2 | 0 | 21% | not testable (Antarctica has no value); gate only |
| Anorthosite, silica, lunar lava flows, pyroclastics | — | fewer than 3 chapters with data | | | not testable |

**Why basalt fails where it is famous:**
- Global maps (Macrostrat, 1:1 M to 1:5 M) give the unit "andesite" at Mt. Etna. At Sunset Crater they give "andesite, dacite, rhyolite, volcanic".
- At Black Point Lava Flow, the printed point falls on the surrounding sandstone.
- At Lonar (Deccan basalt), Mistastin, Pilbara and Barberton, there is no map unit at all.
- At Ibn Battuta, the map says only "sedimentary".

The broad class "volcanic" survives this generalisation; the exact rock does not.

**Half of the catalogue has no Earth layer in the project.** 29 of the 46 feature rows have none:
- impact craters, ejecta, melt and breccia;
- regolith and soils;
- lava tubes, pits, wrinkle ridges, rilles;
- channels, lakes, deltas, gullies, dunes, yardangs;
- hydrothermal deposits.

## 3. Our current protocol at the same sites
A site is "recognised" when its cell reaches the zone rule: median typicality ≥ 0.5 for the target its feature is closest to (fixed before reading).

| Feature | Target compared (slope) | Chapters recognised | Reading |
|---|---|---|---|
| Impact crater (Moon) | polar lit highlands | **0 of 7** | Meteor Crater and the Ries are at the 0th percentile: flat country around a small crater |
| Basalt (Moon) | mare plains | 2 of 8 | Kaʻū Desert 0.82, Lonar 0.65; Etna, Tenerife and Black Point below 0.05 |
| Basalt (Mars) | volcanic plains | 1 of 7 | Etna and Tenerife at the 6th percentile; only a Moroccan point passes |
| Volcanic structure (Mars) | volcanic plains | **0 of 5** | volcanoes are steep; the plains are flat |
| Ground ice (Mars) | ice-rich mid-latitudes | 1 of 5 | the Arctic and Antarctic sites sit at the 4th to 20th percentile |
| Water ice (Moon) | shadowed craters | 5 of 5 | **for their relief, not their ice**: hilly Arctic ground resembles crater walls |
| Collapse pits (Moon) | pits | 2 of 2 | Kīlauea and Iceland, on relief |

**Conclusion:**
- **On slope alone, our protocol does not recognise the sites science classified**, except where relief happens to be the feature.
- **The literature criteria that our data can test do recover them:** the volcanic class and ground ice, as gates.
- **What remains missing** is the data for half of the features, plus a few gates: vegetation, access.

## 4. What a protocol that identifies analogs needs (input for B1 of the [review](../review/expert-panel-2026-11-25.md))
1. **Start from a feature and a use** (Foucher, the catalogue), not from a whole environment. The criteria of each feature combine as gates:
   - the feature present: material or landform;
   - its environment: vegetation, ice, aridity;
   - its practicality: access, permits.

   Relief is one criterion among others, used only where the use needs it: mobility, landing, illumination.
2. **Validate each criterion on the catalogue sites first:** recovered, false alarms, land share, as here. The catalogue becomes the positive controls of each preset, closing E10.
3. **Use data at the scale of the feature:**
   - rocks: a class (volcanic) where only global maps exist;
   - a named rock: only with regional maps;
   - local deposits (sulphates, iron oxides, hydrothermal): an inventory or imaging spectroscopy (EMIT, R35).
4. **Add the missing layers by value for the catalogue:**
   - impact structures: 8 lunar and 7 Martian chapters;
   - vegetation cover: WorldCover, already used for the masks;
   - access: roads;
   - surface materials.

## Limits
- **Catalogue coordinates are sometimes regional centres:** Iceland, Svalbard, Pilbara, the town of Alice Springs, the city of Huelva for Rio Tinto. A 1.6 km sample may miss the feature. This makes recovery a lower bound.
- **A chapter not listed for a feature has not been shown to lack it.** Only the random negatives measure false alarms.
- **The land share is computed only where the run files hold the rule:** basalt, anorthosite, the volcanic class, ground ice, aridity.
- **The catalogue dates from 2012.** It is one expert source, not all of the literature.
