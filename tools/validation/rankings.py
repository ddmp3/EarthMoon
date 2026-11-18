"""Checks the real API rankings against the expected ranking (docs/validation.md).

Expected ranking: each known analog (role = validation) carries in data/candidates.json a known_for field,
the modes it is really used for (Desert RATS, PISCES, AMASE...). An analog need not rank well in the other modes:
a hot desert is not a good analog for a polar colony.

Criteria:
  1. each known analog ranks in the top half of the modes in its known_for (at least 75% of expectations met);
  2. the negative control (role = negative) ranks last or is excluded by the bare-soil filter in every mode;
  3. the best candidate sites (role = candidate) are listed as hypotheses to validate, not as discoveries.

Also reported, for information (not pass/fail):
  * the chance baseline: probability that a random ranking meets at least as many expectations;
  * robustness: share of sensitivity scenarios (weights, tolerances and bounds perturbed, see the API
    `stability` field) in which each expectation is still met;
  * the rank range (10th to 90th percentile) of the best sites.

Usage (API running, e.g. with docker compose up):
    python tools/validation/rankings.py
    python tools/validation/rankings.py --api http://localhost:3001 --markdown docs/validation.md
Exit code: 0 if the criteria are met, 1 otherwise. Standard library only.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import statistics
import sys
import urllib.request

MODES = {"robotics": "Robotics validation", "calibration": "Instrument calibration", "colony": "Self-sufficient colony"}
MIN_SHARE = 0.75
CANDIDATES = os.path.join(os.path.dirname(__file__), "..", "..", "data", "candidates.json")


def fetch_ranking(api: str, mode: str) -> list[dict]:
    req = urllib.request.Request(f"{api}/api/analyze", data=json.dumps({"mode": mode}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)["sites"]


def expected_by_mode(candidates: list[dict]) -> dict[str, set[str]]:
    """Mode -> ids of the known analogs expected in the top half (known_for field)."""
    out: dict[str, set[str]] = {m: set() for m in MODES}
    for s in candidates:
        for m in s.get("known_for", []):
            out.setdefault(m, set()).add(s["id"])
    return out


def _range(site: dict) -> str:
    st = site.get("stability")
    return f"{st['rankP10']}-{st['rankP90']}" if st else "-"


def chance_probability(per_mode: list[tuple[int, int, int]], observed: int) -> float:
    """P(at least `observed` expectations met) if each mode ranked its sites at random.
    per_mode: (ranked sites n, top-half size, expected analogs k). Exact (hypergeometric per mode, convolved);
    the modes are treated as independent, which is only indicative since they share the same sites."""
    dist = [1.0]
    for n, half, k in per_mode:
        pmf = [math.comb(half, j) * math.comb(n - half, k - j) / math.comb(n, k) if 0 <= k - j <= n - half else 0.0
               for j in range(k + 1)]
        new = [0.0] * (len(dist) + k)
        for a, pa in enumerate(dist):
            for b, pb in enumerate(pmf):
                new[a + b] += pa * pb
        dist = new
    return sum(dist[observed:])


def check_mode(sites: list[dict], expected: set[str]) -> dict:
    """Summary of a ranking (pure function, tested)."""
    ranked = [s for s in sites if not s.get("excluded")]
    n = len(ranked)
    rank = {s["id"]: i + 1 for i, s in enumerate(ranked)}
    half = (n + 1) // 2
    negatives = [s for s in sites if s["role"] == "negative"]
    expected_present = sorted(expected & {s["id"] for s in sites})
    met = [i for i in expected_present if rank.get(i, n + 1) <= half]
    missed = [i for i in expected_present if i not in met]
    candidates = [s for s in ranked if s["role"] == "candidate"]
    by_id = {s["id"]: s for s in ranked}
    shares = [(i, by_id[i]["stability"]["topHalfShare"]) for i in expected_present
              if i in by_id and "stability" in by_id[i]]
    coverage = [sum(c["verdict"] != "missing" for c in s["criteria"]) / max(len(s["criteria"]), 1) for s in ranked]
    return {
        "ranked": n,
        "half": half,
        "excluded": [s["id"] for s in sites if s.get("excluded")],
        "expected_met": met,
        "expected_missed": [(i, rank.get(i)) for i in missed],
        "negative_ok": all(s.get("excluded") or rank.get(s["id"]) == n for s in negatives),
        "top_candidates": [(s["id"], s["name"], s["total"]) for s in candidates[:3]],
        "mean_coverage": round(statistics.fmean(coverage), 3) if coverage else 0.0,
        "top": [(rank[s["id"]], s["id"], s["role"], s["total"], _range(s), s.get("confidence", "-")) for s in ranked[:10]],
        "expected_shares": shares,
        "penalized": [(s["id"], s["vegetationFactor"]) for s in ranked if "vegetationFactor" in s],
        "validation": [(rank.get(s["id"]), s["id"], s["total"]) for s in sites if s["role"] == "validation"],
        "failed": [(s["id"], s.get("failedRequirements", [])) for s in ranked if s.get("requirements") == "failed"],
        "confidence": {level: sum(s.get("confidence") == level for s in ranked) for level in ("high", "medium", "low")},
    }


def overall(results: dict[str, dict]) -> dict:
    met = sum(len(s["expected_met"]) for s in results.values())
    total = met + sum(len(s["expected_missed"]) for s in results.values())
    share = met / total if total else 1.0
    negative_ok = all(s["negative_ok"] for s in results.values())
    return {"met": met, "total": total, "share": share, "negative_ok": negative_ok,
            "passes": negative_ok and share >= MIN_SHARE}


def robustness(results: dict[str, dict]) -> dict:
    shares = [sh for r in results.values() for _, sh in r["expected_shares"]]
    fragile = sorted((i, m) for m, r in results.items() for i, sh in r["expected_shares"] if sh < 0.5)
    chance = chance_probability([(r["ranked"], r["half"], len(r["expected_met"]) + len(r["expected_missed"]))
                                 for r in results.values()], overall(results)["met"])
    return {"mean_share": statistics.fmean(shares) if shares else None, "fragile": fragile, "chance": chance}


def to_markdown(results: dict[str, dict]) -> str:
    o = overall(results)
    rb = robustness(results)
    lines = [f"**Verdict: {'met' if o['passes'] else 'not met'}.** Expectations met: {o['met']}/{o['total']} "
             f"({o['share']:.0%}, threshold {MIN_SHARE:.0%}). Negative control excluded or last in every mode: "
             f"{'yes' if o['negative_ok'] else 'no'}.", "",
             "",
             f"Chance baseline: a random ranking would meet at least {o['met']}/{o['total']} expectations "
             f"{rb['chance']:.1%} of the time (modes treated as independent: indicative).",
             ("Robustness: on average each expectation is still met in "
              f"{rb['mean_share']:.0%} of the Monte Carlo scenarios (weights ±50%, tolerances ±25%, bounds ±10%, "
              "site values redrawn within their uncertainty)."
              if rb["mean_share"] is not None else "Robustness: not available (the API returned no stability)."),
             ("Fragile expectations (met in fewer than half of the scenarios): "
              + ", ".join(f"{i} in {m}" for i, m in rb["fragile"]) + ".") if rb["fragile"] else
             "No expectation is fragile (all are met in at least half of the scenarios).",
             "",
             "| Mode | Sites ranked | Expected analogs in the top half | Negative control | Mean criteria coverage |",
             "|---|---|---|---|---|"]
    for mode, s in results.items():
        exp = len(s["expected_met"]) + len(s["expected_missed"])
        lines.append(f"| {MODES[mode]} | {s['ranked']} | {len(s['expected_met'])}/{exp} | "
                     f"{'excluded or last' if s['negative_ok'] else '**not last**'} | {s['mean_coverage']:.0%} |")
    for mode, s in results.items():
        lines += ["", f"### {MODES[mode]}", "", "| Rank | Site | Role | Score | Rank range (80% of scenarios) | Confidence |", "|---|---|---|---|---|---|"]
        lines += [f"| {r} | {i} | {role} | {t} | {rg} | {conf} |" for r, i, role, t, rg, conf in s["top"]]
        lines += ["", f"Expected in the top half (rank ≤ {s['half']}) and present: "
                  + (", ".join(s["expected_met"]) or "none") + "."]
        if s["expected_missed"]:
            lines.append("Expected but lower: " + ", ".join(f"{i} (#{r})" for i, r in s["expected_missed"]) + ".")
        lines.append("All known analogs: " + ", ".join(
            f"{i} ({'excluded' if r is None else f'#{r}'}, {t})" for r, i, t in s["validation"]) + ".")
        lines.append("Best candidate sites (hypotheses to validate): " + ", ".join(f"{n} ({t})" for _, n, t in s["top_candidates"]) + ".")
        if s["failed"]:
            lines.append("Fail a hard requirement (ranked after the others, total kept): "
                         + ", ".join(f"{i} ({', '.join(f)})" for i, f in s["failed"]) + ".")
        if any(s["confidence"].values()):
            c = s["confidence"]
            lines.append(f"Confidence of the assessments: {c['high']} high, {c['medium']} medium, {c['low']} low.")
        if s["penalized"]:
            lines.append("Score lowered by vegetation (NDVI 0.2 to 0.6, factor in brackets): "
                         + ", ".join(f"{i} (×{f})" for i, f in s["penalized"]) + ".")
        if s["excluded"]:
            lines.append("Excluded for dense vegetation (NDVI ≥ 0.6): " + ", ".join(s["excluded"]) + ".")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:3001")
    ap.add_argument("--candidates", default=CANDIDATES)
    ap.add_argument("--markdown", help="Markdown file to write the report into (replaces the block between the markers)")
    args = ap.parse_args(argv)
    with open(args.candidates, encoding="utf-8") as f:
        expected = expected_by_mode(json.load(f))
    results = {m: check_mode(fetch_ranking(args.api.rstrip("/"), m), expected[m]) for m in MODES}
    report = to_markdown(results)
    print(report)
    if args.markdown:
        start, end = "<!-- rankings:start -->", "<!-- rankings:end -->"
        with open(args.markdown, encoding="utf-8") as f:
            doc = f.read()
        if start not in doc or end not in doc:
            sys.exit(f"{args.markdown}: markers {start} and {end} not found")
        head, rest = doc.split(start, 1)
        _, tail = rest.split(end, 1)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(f"{head}{start}\n{report}{end}{tail}")
    return 0 if overall(results)["passes"] else 1


if __name__ == "__main__":
    sys.exit(main())
