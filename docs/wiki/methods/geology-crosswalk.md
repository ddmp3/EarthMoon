# Geology crosswalk: Earth lithology against lunar environments (T46, decision E17)

**Status: expert decision E17, delegated by David to Claude on 20/11/2026 ("do what is best"). Taken as proposed below; to be reviewed by lunar geologists before G5.**

## Source
- **Earth:** Macrostrat (API v2 and `carto` vector tiles, CC-BY 4.0, David's choice of 20/11/2026). Each map unit has a lithology text and lithology ids from the Macrostrat definitions (214 lithologies, `class` > `type` > `group`).
  - Coverage is uneven. Most regions have a small-scale map (1:5M, such as the Geologic Map of North America). Some have only the world map at 1:35M (Chorlton 2007, source 154), which says, for example, "intrusive igneous rocks" and nothing more.
- **Moon:** the composition of each target environment, from verified references and catalogue entries:
  - south polar highlands: feldspathic, anorthositic [R15];
  - maria: basalt (Unified Geologic Map of the Moon, catalogue `usgs-unified-geologic-map`);
  - pits: most in impact melt, a few in maria [R17].

## Four states per Earth map unit, for each environment
- **match:** the same rock family as the lunar surface material.
- **partial:** a related rock: same minerals in other proportions, or the same composition with another texture.
- **no match:** a known lithology of another family.
- **unresolved:** the map says only "igneous", "plutonic", "volcanic" or "mafic", or has no lithology. This is **never** shown as "no match". The UI shows it as missing data (hatched), with the map scale.

The geology dimension is reported on its own, never averaged with slope (T23, E5).

## Proposed table (Macrostrat lithology ids)

| Lunar environment | match | partial | unresolved | Basis |
|---|---|---|---|---|
| Lit highlands, shadowed regions, polar cap | anorthosite (101) | norite (108), troctolite (105), gabbro (59), metagabbro (171) | igneous (95), plutonic (52), mafic (161) | R15 (anorthositic highlands); R54 (Mistastin anorthositic impact melt); R41 (highland simulant made of anorthosite and norite) |
| Mare plains | basalt (70) | dolerite (152), diabase (94), metabasalt (170), basanite (196), picrite (216), mafite (73) | igneous (95), volcanic (63), mafic (161) | Unified Geologic Map (mare units are basalt) |
| Pits | none | basalt (70) | igneous (95), volcanic (63), mafic (161) | R17 (pits mostly in impact melt, a few in maria); R56 (basaltic lava tubes on Earth) |

Every other lithology with a known class is "no match" for all three rows.

## The five choices of E17 (all taken as proposed)
1. **Partial matches for the highlands.** Should norite, troctolite, gabbro and metagabbro count as partial? The basis is that they are plagioclase-bearing mafic plutonic rocks, and R41 uses norite in a highland simulant. Or should only anorthosite count?
2. **Mare plains.** Should dolerite, diabase (same composition as basalt, intrusive texture) and metabasalt count as partial?
3. **Pits.** No Earth rock stands for lunar impact melt, so the proposal has no full match. Is basalt (lava-tube setting) right as a partial match?
4. **Generic "mafic volcanic rocks".** The proposal keeps them **unresolved**, not partial: a map that says only "mafic volcanic" cannot tell basalt from other mafic rocks.
5. **Map units with several lithologies.** For example "sandstone, basalt", or the Deccan's "flood basalt; mafic volcanic rocks; basalt". The proposal: when Macrostrat marks a Major lithology, use the best state among the Major lithologies only; otherwise use the best state among all, with the flag "mixed unit". So the Deccan is a match (basalt is listed), and "sandstone, basalt" is a match flagged as mixed.

## Known limits (already measured on 20/11/2026)
- Mistastin and Nain (Labrador, named anorthositic analogs in v2) are covered only by the 1:35M world map. They will be **unresolved**, not matched.
- Lac-Saint-Jean and the Marcy massif (Adirondacks) are recognized as anorthosite (1:5M and finer).
- Holuhraun is recognized as basalt. The Deccan traps appear only on the world map, as "flood basalt; mafic volcanic rocks; basalt" (lithology ids 63, 70, 161): a match under question 5.
- A lithology class is not a mineralogy, and a mineralogy is not regolith mechanics (to be written in `docs/LIMITS.md`).
