"""Reference scorer in Python, independent of the TypeScript engine (apps/api/src/scoring).

It scores the frozen data set with the scenario definitions of methodology v2 and must give the same totals,
coverage and requirement outcomes as POST /api/analyze: data/reference/expected-rankings-v2.json is written
by this script and checked by the API tests.

    python score_sites.py                       # prints the three rankings on data/dataset-v2.json
    python score_sites.py --mode colony
    python score_sites.py --write-expected      # rewrites data/reference/expected-rankings-v2.json
    python score_sites.py --v1                  # methodology v1 criteria (baseline of docs/SCIENTIFIC_VALIDATION.md)

Rules (docs/SCIENTIFIC_METHODOLOGY.md):
  * criterion score = 1 inside [min, max]; linear decay to 0 at the tolerance (toleranceBelow / toleranceAbove
    when the two sides differ)
  * total = sum(w * score) / sum(w) over the criteria that have a value, out of 100
  * coverage = share of the weight that has a value; a missing value counts neither for nor against the site
  * a required criterion scoring 0 fails the scenario: the site ranks after every site that passes
  * common vegetation filter: total multiplied by 1 up to NDVI 0.2, linear down to 0 at NDVI 0.6 (excluded)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

NDVI_MAX = 0.2
NDVI_DENSE = 0.6
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
SCENARIOS_FILE = os.path.join(DATA, "reference", "scenarios-v2.json")
DATASET_FILE = os.path.join(DATA, "dataset-v2.json")
CANDIDATES_FILE = os.path.join(DATA, "candidates.json")
EXPECTED_FILE = os.path.join(DATA, "reference", "expected-rankings-v2.json")


def C(param, lo=None, hi=None, tolerance=0.0, weight=1.0) -> dict:
    c = {"param": param, "tolerance": tolerance, "weight": weight}
    if lo is not None:
        c["min"] = lo
    if hi is not None:
        c["max"] = hi
    return c


# Methodology v1 (before the scientific audit), kept to reproduce the baseline of docs/SCIENTIFIC_VALIDATION.md.
MODES_V1: dict[str, list[dict]] = {
    "robotics": [
        C("slope_mean", 5, 13, 10, 3), C("slope_max", 15, 30, 10, 1), C("roughness", 22, 65, 30, 2),
        C("precipitation", None, 1, 1, 1), C("t2m_min", None, -20, 20, 1), C("lst_amplitude", 20, None, 15, 1),
        C("volcano_distance", None, 50, 100, 1),
    ],
    "calibration": [
        C("t2m_mean", None, 0, 10, 2), C("volcano_distance", None, 50, 100, 1), C("wind", None, 3, 3, 2),
        C("humidity", None, 40, 30, 2), C("precipitation", None, 0.5, 1, 1), C("quake_count", None, 5, 20, 3),
        C("lst_amplitude", 25, None, 15, 2), C("t2m_min", None, -30, 20, 1),
    ],
    "colony": [
        C("t2m_mean", None, -5, 10, 3), C("latitude_abs", 65, None, 15, 2), C("solar", 2, None, 2, 1),
        C("slope_mean", None, 5, 5, 3), C("volcano_distance", None, 100, 200, 1), C("quake_count", None, 10, 30, 2),
        C("t2m_min", None, -30, 20, 1),
    ],
}


def load_modes(path: str = SCENARIOS_FILE) -> dict[str, list[dict]]:
    with open(path, encoding="utf-8") as fh:
        return {mode_id: mode["criteria"] for mode_id, mode in json.load(fh)["modes"].items()}


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def js_round(x: float) -> int:
    """Rounds half up, like JavaScript Math.round (Python rounds half to even)."""
    return math.floor(x + 0.5)


def criterion_score(value, criterion: dict) -> float:
    """1 inside the interval, linear decay to 0 at the tolerance outside it."""
    lo, hi, tol = criterion.get("min"), criterion.get("max"), float(criterion.get("tolerance", 0))
    if lo is not None and hi is not None and lo > hi:
        raise ValueError(f"criterion {criterion['param']}: min > max")
    if tol < 0:
        raise ValueError(f"criterion {criterion['param']}: negative tolerance")
    dist = 0.0
    if lo is not None and value < lo:
        dist, tol = lo - value, float(criterion.get("toleranceBelow", tol))
    elif hi is not None and value > hi:
        dist, tol = value - hi, float(criterion.get("toleranceAbove", tol))
    if dist == 0:
        return 1.0
    return max(0.0, 1.0 - dist / tol) if tol > 0 else 0.0


def verdict(score: float) -> str:
    return "match" if score >= 0.7 else "partial" if score >= 0.4 else "mismatch"


def vegetation_factor(ndvi) -> float:
    """1 up to NDVI 0.2, linear decrease to 0 at NDVI 0.6; 1 if NDVI is unknown."""
    if not _is_number(ndvi) or ndvi <= NDVI_MAX:
        return 1.0
    return max(0.0, 1.0 - (ndvi - NDVI_MAX) / (NDVI_DENSE - NDVI_MAX))


def assess(values: dict, criteria: list[dict]) -> dict:
    """Unrounded total, coverage, bounds and requirement outcome (same definitions as the TypeScript `assess`)."""
    out, weighted, known, total_weight = [], 0.0, 0.0, 0.0
    failed, missing, required_unknown = [], [], False
    for c in criteria:
        w = float(c.get("weight", 1))
        if w <= 0:
            raise ValueError(f"criterion {c['param']}: weight must be positive")
        total_weight += w
        v = values.get(c["param"])
        if not _is_number(v):
            out.append({"param": c["param"], "value": None, "score": 0, "verdict": "missing"})
            missing.append(c["param"])
            required_unknown = required_unknown or bool(c.get("required"))
            continue
        s = criterion_score(v, c)
        out.append({"param": c["param"], "value": v, "score": round(s, 3), "verdict": verdict(s)})
        weighted += w * s
        known += w
        if c.get("required") and s == 0:
            failed.append(c["param"])
    return {
        "total": 100 * weighted / known if known > 0 else 0.0,
        "coverage": known / total_weight if total_weight > 0 else 0.0,
        "total_min": 100 * weighted / total_weight if total_weight > 0 else 0.0,
        "total_max": 100 * (weighted + total_weight - known) / total_weight if total_weight > 0 else 0.0,
        "requirements": "failed" if failed else "unknown" if required_unknown else "met",
        "failed": failed,
        "missing": missing,
        "criteria": out,
    }


def score_site(values: dict, criteria: list[dict], missing: str = "skip", factor: float = 1.0) -> dict:
    """Returns {"total": 0-100, "criteria": [...]}. `missing="zero"` counts a missing value as 0 (lower bound)."""
    if missing not in ("skip", "zero"):
        raise ValueError("missing must be 'skip' or 'zero'")
    a = assess(values, criteria)
    total = a["total"] if missing == "skip" else a["total_min"]
    return {"total": js_round(total * factor), "criteria": a["criteria"]}


def analyze(sites: list[dict], mode: str | None = None, criteria: list[dict] | None = None,
            ndvi_filter: bool = True, missing: str = "skip", modes: dict[str, list[dict]] | None = None) -> dict:
    """sites: [{id, name, lat, lon, role, values}]. Returns the ranked sites, same order as POST /api/analyze:
    sites failing a hard requirement after the others, then by descending total. Sites with dense vegetation
    are listed under "excluded"."""
    modes = modes if modes is not None else load_modes()
    if criteria is None:
        if mode not in modes:
            raise ValueError(f"mode must be one of {sorted(modes)} (or pass criteria)")
        criteria = modes[mode]
    ranked, excluded = [], []
    for s in sites:
        vals = s.get("values") or {}
        ndvi = vals.get("ndvi")
        factor = vegetation_factor(ndvi) if ndvi_filter else 1.0
        if factor == 0:
            excluded.append({"id": s["id"], "name": s.get("name"), "reason": f"ndvi {ndvi} >= {NDVI_DENSE}"})
            continue
        a = assess(vals, criteria)
        total = a["total"] if missing == "skip" else a["total_min"]
        site = {"id": s["id"], "name": s.get("name"), "lat": s.get("lat"), "lon": s.get("lon"), "role": s.get("role"),
                "total": js_round(total * factor), "criteria": a["criteria"],
                "coverage": js_round(a["coverage"] * 100) / 100, "requirements": a["requirements"],
                "total_range": [js_round(a["total_min"] * factor), js_round(a["total_max"] * factor)]}
        if a["failed"]:
            site["failed_requirements"] = a["failed"]
        if a["missing"]:
            site["missing"] = a["missing"]
        if factor < 1:
            site["vegetation_factor"] = round(factor, 2)
        ranked.append(site)
    ranked.sort(key=lambda x: (x["requirements"] == "failed", -x["total"], x["id"]))
    res = {"mode": mode if mode in modes else "custom", "sites": ranked}
    if excluded:
        res["excluded"] = excluded
    return res


def dataset_sites(dataset_path: str = DATASET_FILE, candidates_path: str = CANDIDATES_FILE) -> list[dict]:
    """Sites of the frozen data set in the shape expected by `analyze`."""
    with open(dataset_path, encoding="utf-8") as fh:
        dataset = json.load(fh)["sites"]
    with open(candidates_path, encoding="utf-8") as fh:
        candidates = json.load(fh)
    return [{"id": c["id"], "name": c["name"], "lat": c["lat"], "lon": c["lon"], "role": c.get("role", "candidate"),
             "values": {k: e["value"] for k, e in dataset[c["id"]]["values"].items()}}
            for c in candidates if c["id"] in dataset]


def expected_rankings(sites: list[dict], modes: dict[str, list[dict]]) -> dict:
    out = {}
    for mode in modes:
        res = analyze(sites, mode, modes=modes)
        rows = [{"id": s["id"], "total": s["total"], "requirements": s["requirements"], "coverage": s["coverage"]}
                for s in res["sites"]]
        rows += [{"id": e["id"], "total": 0, "requirements": None, "coverage": None} for e in res.get("excluded", [])]
        out[mode] = rows
    return out


def _print(res: dict) -> None:
    print(f"mode: {res['mode']}")
    for rank, s in enumerate(res["sites"], 1):
        note = "" if s["requirements"] == "met" else f"  requirements {s['requirements']}: {s.get('failed_requirements', s.get('missing'))}"
        print(f"{rank:>3}. {s['total']:>3}/100  {s['id']:<24} coverage {s['coverage']:.2f}{note}")
    for e in res.get("excluded", []):
        print(f"excluded  {e['id']}: {e['reason']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sites", nargs="?", help="optional JSON {'sites': [...]} with 'values'; default: data/dataset-v2.json")
    ap.add_argument("--mode", default=None)
    ap.add_argument("--v1", action="store_true", help="use the methodology v1 criteria")
    ap.add_argument("--no-ndvi-filter", action="store_true")
    ap.add_argument("--missing", choices=("skip", "zero"), default="skip")
    ap.add_argument("--write-expected", action="store_true")
    a = ap.parse_args(argv)
    modes = MODES_V1 if a.v1 else load_modes()
    if a.sites:
        with open(a.sites, encoding="utf-8") as fh:
            data = json.load(fh)
        sites = data["sites"] if isinstance(data, dict) else data
    else:
        sites = dataset_sites()
    if a.write_expected:
        payload = {"description": "Totals, requirement outcomes and coverage of every site on data/dataset-v2.json, computed by "
                                  "tools/scoring/score_sites.py. The API tests check that the TypeScript engine gives the same.",
                   "methodology": "2.0.0", "modes": expected_rankings(sites, modes)}
        with open(EXPECTED_FILE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"written: {EXPECTED_FILE}")
        return 0
    for mode in ([a.mode] if a.mode else list(modes)):
        _print(analyze(sites, mode, ndvi_filter=not a.no_ndvi_filter, missing=a.missing, modes=modes))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
