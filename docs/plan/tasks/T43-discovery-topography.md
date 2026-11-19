# T43 First global discovery run (topography) and validation

Read first: `CLAUDE.md`, `docs/plan/README.md` sections 1 to 3, `docs/VALIDATION_PROTOCOL.md` and the tag `validation-protocol-v1` (T25), and the outputs of T40 to T42. Branch: `feat/T43-discovery-run`.

## Goal
The first defensible global result: where on Earth the terrain resembles each lunar environment at the chosen scales, for scenarios A and B. It is validated with the frozen protocol.

## Steps
1. Check that `validation-protocol-v1` exists and that the control lists have not changed since (`git diff validation-protocol-v1 -- data/validation`). If they changed, stop and tell David.
2. Run the coarse global stage, refine, extract the zones (rule from T26) and run the Monte Carlo.
3. Apply the protocol: percentiles of the positive controls, the negative-control false-positive rate, self-consistency, the bias analysis, and the reproducibility rebuild.
4. **Unexpected candidates:** write one short dossier per top-N unknown zone (`docs/wiki/runs/run-001/zones/<id>.md`) with an outcome: plausible, artefact, or unknown.
5. Report in `docs/wiki/runs/run-001.md` (numbers, maps as PNG, failures included) and a one-page summary in `docs/VALIDATION.md`.

## Rules
- Do not change thresholds or metrics after seeing results. If something is wrong, open a new protocol version (`validation-protocol-v2`), say why, and rerun everything.
- Unfavourable results are reported first, not last.

## Done when
The report is complete and the checks pass. Gate G4: David reviews the map and the report.

## Added by T14 (18/11/2026)
- South of 60°S WorldCover has no tile (T40). Use `add-rock-outcrop-v7-3` as the mask there: outside the rock polygons is ice or snow. Lithology there: `scar-geomap-v2022-08`.

## As built (19/11/2026)
- **Protocol:** v2, tagged before run-001. The engine masks the 7 hidden-ground classes, and the masks check reads 1 km windows (David, 18/11).
- **Code:** `screen.py`, `antarctic.py`, `prefetch.py`, `discover.py`, `zones.py`, `validate_run.py`, `checks.py`, `dossier.py`. Copernicus is downloaded once with 96 connections and read locally for both scales.
- **Report:** `docs/wiki/runs/run-001.md`; summary in `docs/VALIDATION.md`; dossiers in `docs/wiki/runs/run-001/zones/`.
- **For run-002 (protocol v3):** rank zones on high-confidence cells, and merge cell parts cut by tile edges.
