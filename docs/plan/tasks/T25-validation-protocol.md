# T25 Uncertainty and independent validation protocol (written before any result)

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/SCIENTIFIC_VALIDATION.md`, `docs/wiki/methods/comparison.md` and `docs/SCENARIOS.md`. Branch: `docs/T25-validation`.

## Goal
A validation protocol that cannot be tuned to the team's expectations, frozen in git before the first discovery run (T43).

## Context
- In v2, the expectations (`known_for` in `data/candidates.json`) were written by the team that built the model. There is one negative control. Result: 8 of 11 expectations met, not retuned. Finding L6: a global search will produce many false positives that must be measured.
- The v2 Monte Carlo (`apps/api/src/scoring/sensitivity.ts`) perturbs weights (±50%), tolerances (±25%) and bounds (±10%), and redraws values that have a sigma. Seed 20261115, 500 runs.

## Steps
1. **Positive controls per scenario,** chosen by a written inclusion rule. For example: a place used in a published analog campaign for that function, with the citation (verified, T13). The rule is written before the list, and the list is written before any v3 result.
2. **Negative controls:** at least 10 per scenario, chosen by rule (for example random land cells stratified by biome, seed fixed) and not by intuition.
3. **Metrics:**
   - percentile of each positive control among all evaluated cells;
   - share of positives in the top k%;
   - false-positive rate on negatives;
   - planetary self-consistency (from T23).
   Define the pass thresholds now.
4. **Uncertainty:** extend the Monte Carlo to data sigma, the choice of scale (T22), the choice of metric (T23), the thresholds of the requirements, and the reference environment boundaries. State what is still not covered.
5. **Bias:**
   - coverage and results by latitude band and continent;
   - dependence on a single source;
   - sensitivity to resolution.
6. **Unexpected candidates:** the top N zones not in any control list each get a short dossier (data, imagery, literature search) and one outcome: plausible, explained artefact, or unknown. Artefacts are reported, not tuned away.
7. **Reproducibility:** a rebuild from the manifests gives identical hashes.

## Outputs
- `docs/VALIDATION_PROTOCOL.md` (short).
- `data/validation/controls-<scenario>.yaml`, committed **and tagged** (`git tag validation-protocol-v1`) before T43 starts.

## Done when
The tag exists; David has read the protocol (part of gate G2).
