# How sites are selected: multi-criteria, by use (T54, 25/11/2026)

**In one sentence:** we choose analog sites the way the literature does. Each use has its criteria. The required ones are applied together, and the result is checked at once on the analog sites science already knows.

## Where it comes from
The [known-analogs audit](../validation/known-analogs.md) (T53) read how analog sites are chosen:
- **Foucher et al. 2021 (R28):** an analog is defined by its **use**: "focus on the specific properties that need to be imitated".
- **The ESA/Open University catalogue (R66):** Earth sites are assigned **per feature** of the Moon or Mars. The experts' order is: scientific merit and relevance first, then cost, access (permits, physical access) and infrastructure.
- **NASA field campaigns:**
  - Mauna Kea (R68): three criteria, all needed: applicability (terrain, rocks, regolith), access, infrastructure.
  - Cinder Lake (R69): five criteria: topography, access, vegetation cover, signal, geologic diversity.
- **Nobody uses one criterion alone.** Preston and Dartnell (R65) add that there are "no clearly defined and followed criteria": the criteria must therefore be **visible and open to discussion**.

Our first method compared one property (slope at 1 to 11.6 km) to one planetary environment. On the known sites it recognised almost none (T53).

## The method
1. **A preset is a use.** It states what it imitates on the Moon or Mars, and lists its criteria. Each criterion has its reason and its source. The presets are in [presets.yaml](../../../data/presets/presets.yaml).
2. **A criterion is a readable condition** on one variable, for example `permafrost >= 0.5`, or an equation written by the user.
3. **Required criteria are gates**, applied together:
   - every one met: the cell is a **candidate**;
   - one failed: the cell is **excluded**;
   - one unknown (missing data): the cell is **to check**. Missing data is never a bad value.
4. **Preferred criteria never exclude.** They order the candidates by how many are met, with no weights. Ties go to fewer unknowns, then to the confidence of the relief values.
5. **Every rule, preset or edited, is checked on:**
   - the catalogue sites listed for its features (recovered when one of a site's points is a candidate);
   - the 18 random negatives of the protocol (false alarms);
   - the share of assessed land that passes. A rule passing much of the land is a gate, not a discriminator.
6. **A rule that differs from its preset is labelled "custom, not validated".** It never changes a published result.

## The variables
All come from the release, already computed: no external source is read at request time (ADR-005).

| Variable | What it is | Data |
|---|---|---|
| `relief_<target>` | Typicality of the cell's slopes for a planetary environment (0 to 1) | Copernicus DEM against LOLA or MOLA (protocol v3, mars-v3) |
| `basalt`, `basalt_or_related`, `anorthosite`, `anorthosite_or_related`, `volcanic_rock` | Share of the cell's resolved map samples with that rock; unknown where no map unit | Macrostrat, 1:1 M to 1:5 M |
| `hidden_ground` | Share of the cell's windows hidden by vegetation, crops, buildings or water | ESA WorldCover 2021 |
| `permafrost` | Permafrost probability; unknown in the Southern Hemisphere | Obu et al. 2019 (R32) |
| `aridity` | Aridity index (below 0.2: arid) | Global Aridity Index v3 |
| `confidence` | Confidence of the relief values (0, 1, 2) | protocol v3 |
| `base_slope_ok`, `climb_lrv_ok`, `climb_viper_ok` | Slope requirements of scenarios A and B (1 met, 0 not) | Copernicus GLO-30 |

**Equations** use numbers, these names, `+ - * /`, comparisons, `and`, `or`, `not`, `min`, `max` and `abs`:
- they are parsed by a small grammar, never run as code;
- logic is three-valued: "unknown and false" is false, "unknown or false" is unknown;
- weights written in an equation are the author's, and should be tested.

## The presets and their check on known sites
Measured on the current releases, 25/11/2026: Moon `r-bd4da8c0`, Mars `r-4fea11f8`.

| Preset | Required | Known sites recovered (with data) | False alarms (of 18) | Land passing |
|---|---|---|---|---|
| Volcanic geology of Mars | volcanic rock, bare ground | 5 of 12 | 0 | 1.5% |
| Ground ice (Mars mid-latitudes; north and south polar variants) | permafrost ≥ 0.5, bare ground | 4 of 6 (1 without data) | 0 | 4.6% |
| Ice in lunar cold traps | permafrost ≥ 0.5, bare ground | 4 of 5 | 0 | 5.2% |
| Basalt of the lunar maria | basalt or related rock, bare ground | 2 of 9 | 0 | 0.8% |
| Lava pits and tubes | basalt or related rock, bare ground | 2 of 2 (Iceland, Kīlauea) | 0 | 0.8% |
| Rover mobility on lunar polar relief | within the Apollo rover limit, bare ground | 3 of 3 | 0 | 38.9% (gate only) |
| Terrain of a polar base | base slope ≤ 10°, bare ground | 4 of 8 | 0 | 34.8% (gate only) |

**Read these numbers with their limits:**
- **They are a development check, not an independent one.**
  - The thresholds tested in T53 kept their values.
  - The bare-ground gate is the zone rule of protocol v3, added because T53 showed boreal forest passing the ice rule.
  - The 1 km relief became *preferred* in the rover and base presets after this check. Required, it excluded every known test site (3 of 3 and 8 of 8). Rover test sites are chosen for terrain at the rover's scale (R69), which needs 30 m windows (review, D1).
- **Global geological maps miss famous rocks** (Etna is mapped as "andesite"). A site excluded for its rock is often a map limit, not a bad site: the panel shows which criterion excluded it.
- **The gates of mobility and base terrain pass much of the dry land.** They are gates, not discriminators, until terrain at the scale of the use and access data exist.

## In the interface
- In every mission, the **Selection criteria** panel opens on the mission's use, already run.
- Each criterion shows its role (required or preferred), its condition, its reason and its source. Thresholds, roles and variables can be changed, criteria added or removed, and an equation written.
- **Test these criteria** gives:
  - the candidate cells, listed and on the map;
  - the counts and land share;
  - the known sites recovered or not, with the criterion that excluded each one;
  - the false alarms.
- The single-environment selector is gone: the use decides the environment. The layer selector only chooses what the map shows.
