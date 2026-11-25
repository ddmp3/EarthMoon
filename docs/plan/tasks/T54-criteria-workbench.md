# T54 Criteria workbench: see, edit and test the selection criteria

Read first: `CLAUDE.md`, `docs/plan/README.md`, [T53](T53-known-analogs.md) and its [report](../../wiki/validation/known-analogs.md), ADR-005 (on-demand compute). Branch: `feat/T54-criteria-workbench`.

## Goal (David, 25/11/2026)
- "The selection criteria must be easy to identify and to change from the interface. I must be able to adjust the parameters easily, to align with the scientific needs."
- "A scientist must be able to test their selection algorithm or their equation, to validate that their criteria are good, and see the results."

## Decisions (David, 25/11/2026)
- "Apply the best practices you documented. The criteria must be readable and the method clear and understandable."
- **Applied from T53:**
  - one preset per use, with what it imitates;
  - required criteria are gates applied together (catalogue R66, NASA R68 and R69);
  - preferred criteria only order the candidates, with no weights;
  - every criterion carries its reason and its source;
  - every rule is checked on the catalogue's known sites;
  - the single-environment selector is removed from the missions.
- Method page: [wiki/methods/criteria](../../wiki/methods/criteria.md).

## What the user gets
1. **Every criterion is visible:** for each feature and use, the user sees:
   - its rule;
   - its data and the scale of that data;
   - its threshold;
   - the source that justifies it (literature quote, or "chosen by the project").

   The frozen protocol criteria are shown read-only, labelled with their protocol version.
2. **Every parameter can be edited:**
   - thresholds;
   - the rock lists, chosen from Macrostrat names and types;
   - which gates apply;
   - the target and the scale used for relief.
3. **A rule or an equation can be written:**
   - **Gates:** conditions joined by AND or OR. For example: volcanic rock AND permafrost probability ≥ 0.5 AND bare ground ≥ 50%.
   - **Equation:** an expression over the named variables of the cell, compared with a threshold. Allowed: arithmetic, comparisons, `and`, `or`, `not`, `min`, `max`, `abs`.
   - The equation is parsed by a small grammar, never by `eval`. Unknown names are refused with the list of valid ones.
4. **Each test shows its results at once:**
   - known sites of the catalogue (R66) recovered per feature, with each site, its values and why it passes or fails;
   - false alarms among the 18 random negatives;
   - the share of land that passes;
   - the passing cells on the map.

   The scores of the frozen criteria are shown beside the user's, for comparison.
5. **The result is labelled and reproducible:**
   - a custom rule is labelled "custom, not validated";
   - the rule, the data release and the code version give a test id;
   - the rule can be exported and imported as YAML;
   - a shared link replays it.

## Rules kept
- **Frozen protocols stay frozen:** a custom rule never changes a published result. It can become a new protocol version only by David's decision, frozen before any run.
- **Missing data is never a bad value:** a site or cell without a value is "unknown" and counted apart.
- **No weights hidden:** an equation states its own; the interface shows the sensitivity of the result to each coefficient (±10%).
- **On-demand compute over the precomputed cells and site table only (ADR-005):** no external fetch at request time.

## Design (to confirm with David at the first review)
- **Data:**
  - one table per body, with one row per 5 km cell and one column per variable already computed: slope typicality per target, geology shares, permafrost, aridity, hidden share, confidence;
  - plus the T53 site table (catalogue points and negatives) with the same columns.
- **Service:** `apps/discovery` gains `POST /criteria/test`, which takes a rule and a body. It returns:
  - recovery per feature, and false alarms;
  - land share;
  - the cell ids passing, capped and tiled for the map.

  It is called through the Node API, with a contract test.
- **Interface:**
  - a "Criteria" panel in each mission, in the same design, in French and English;
  - the variables list, with their unit, data source and scale;
  - the rule editor (form for gates, text field for the equation, with live parse errors);
  - the results table and the map layer.

## Steps (TDD)
1. Variable table builder (Python), from the run files; tests on synthetic cells.
2. Rule grammar and evaluator (Python), with tests: precedence, unknown names, missing values, no code execution.
3. `/criteria/test` in the discovery service, and its forwarding in the Node API (OpenAPI, contract test).
4. Interface panel; e2e and UI audit (desktop and phone).
5. Docs: a short user page, and the method page in the wiki.

## Done when
- David changes a threshold or writes an equation in the interface and sees, within seconds:
  - the catalogue sites recovered;
  - the false alarms;
  - the land share;
  - the map.
- The frozen criteria are visible beside the user's, with their sources.
