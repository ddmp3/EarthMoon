# T53 Known analog sites: the criteria science uses, and what our protocol misses

Read first: `CLAUDE.md`, `docs/plan/README.md`, [review 25/11](../review-2026-11-25.md), `docs/VALIDATION_PROTOCOL.md`. Branch: `feat/T53-known-analogs`.

## Goal (David, 25/11/2026)
"Science has already classified sites as analogs and defined the criteria for it."
1. Take each criterion and identify the analog sites that science classified under it.
2. List every criterion needed to revalidate those known sites, and the data each one needs.
3. Check whether our comparison protocol respects those criteria.
4. Check our results at those sites.
5. **Not the whole planet:** a few known sites and their data, to validate the protocol that identifies analog sites.

This complements the review of 25/11 (presets, controls on the right dimension). It changes no method and no release. It is an audit.

## Independent source of the sites and criteria
- **The Catalogue of Planetary Analogues** (Preston, Grady and Barber, Open University, for ESA, CAFE study, final version 5 December 2012). It lists:
  - lunar and Martian features;
  - for each feature, the Earth sites that represent it;
  - per site: coordinates, environment, access, permits and infrastructure.
- Written by planetary scientists, before this project and independently of it. Extract and provenance: `data/validation/known-analogs/catalogue.yaml`.
- Criteria in the literature (verified texts): `data/validation/known-analogs/criteria.yaml`.

## Rules frozen before any result (commit of this file)
- **Sites:** every catalogue site with a usable coordinate (one point per chapter, plus its site-specific points). Exclusions are listed with their reason, before any value is read.
- **Features:** the catalogue directory, as printed (feature → chapters).
- **Earth criterion per feature:** fixed in `criteria.yaml`, with its data source. Features without an Earth data layer are listed as "no data", with the data they would need.
- **A feature is found at a chapter** when it is found at one or more of its points. Each point is assessed as the centre plus 8 points at 1.6 km (the sampling of `geology.py`).
- **Pass rules, per feature:**
  - recovery: found at 75% or more of the chapters that list it and have data, with at least 3 such chapters (otherwise "not testable");
  - false alarms: at most 1 of the 18 random negatives of the protocol (`negatives.yaml`);
  - base rate: the share of land cells where the strict rule holds, reported where existing run files allow it. A rule that passes more than 10% of the land does not discriminate on its own: it is a gate, not a discriminator.
- **Our current protocol at these sites:** for each feature with a matching target, the cell's median typicality for that target. "Recognised" means median ≥ 0.5, the zone rule. The percentile among assessed cells is also reported.

## Steps (TDD)
1. Freeze the catalogue extract, the criteria and this task (one commit, before any value).
2. `tools/validation/known_analogs.py`: coordinate parser, rules, extraction from the cached Macrostrat tiles and run files; tests first.
3. Run on the sites, then write `data/runs/known-analogs/results.json` and [wiki/validation/known-analogs](../../wiki/validation/known-analogs.md).
4. Plan, changelog, PR.

## Done when
- Each feature of the catalogue has a criterion, its data, and a verdict: recovered or not, discriminating or not, or no data.
- Our current protocol is shown at each site.
- The gaps between the criteria science uses and what we compare are listed, with what it would take to close each one.
