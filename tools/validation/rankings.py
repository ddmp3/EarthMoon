"""Checks the real API rankings against the expected ranking (docs/validation.md).

Expected ranking: each known analog (role = validation) carries in data/candidates.json a known_for field,
the modes it is really used for (Desert RATS, PISCES, AMASE...). An analog need not rank well in the other modes:
a hot desert is not a good analog for a polar colony.

Criteria:
  1. each known analog ranks in the top half of the modes in its known_for (at least 75% of expectations met);
  2. the negative control (role = negative) ranks last or is excluded by the bare-soil filter in every mode;
  3. the best understudied sites (role = candidate) are listed as possible discoveries.

Usage (API running, e.g. with docker compose up):
    python tools/validation/rankings.py
    python tools/validation/rankings.py --api http://localhost:3001 --markdown docs/validation.md
Exit code: 0 if the criteria are met, 1 otherwise. Standard library only.
"""
from __future__ import annotations
import argparse
import json
import os
import statistics
import sys
import urllib.request

MODES = {"robotics": "Validation robotique", "calibration": "Calibration d'instruments", "colony": "Colonie autosuffisante"}
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
        "top": [(rank[s["id"]], s["id"], s["role"], s["total"]) for s in ranked[:10]],
        "validation": [(rank.get(s["id"]), s["id"], s["total"]) for s in sites if s["role"] == "validation"],
    }


def overall(results: dict[str, dict]) -> dict:
    met = sum(len(s["expected_met"]) for s in results.values())
    total = met + sum(len(s["expected_missed"]) for s in results.values())
    share = met / total if total else 1.0
    negative_ok = all(s["negative_ok"] for s in results.values())
    return {"met": met, "total": total, "share": share, "negative_ok": negative_ok,
            "passes": negative_ok and share >= MIN_SHARE}


def to_markdown(results: dict[str, dict]) -> str:
    o = overall(results)
    lines = [f"**Verdict: {'met' if o['passes'] else 'not met'}.** Expectations met: {o['met']}/{o['total']} "
             f"({o['share']:.0%}, threshold {MIN_SHARE:.0%}). Negative control excluded or last in every mode: "
             f"{'yes' if o['negative_ok'] else 'no'}.", "",
             "| Mode | Sites ranked | Expected analogs in the top half | Negative control | Mean criteria coverage |",
             "|---|---|---|---|---|"]
    for mode, s in results.items():
        exp = len(s["expected_met"]) + len(s["expected_missed"])
        lines.append(f"| {MODES[mode]} | {s['ranked']} | {len(s['expected_met'])}/{exp} | "
                     f"{'excluded or last' if s['negative_ok'] else '**not last**'} | {s['mean_coverage']:.0%} |")
    for mode, s in results.items():
        lines += ["", f"### {MODES[mode]}", "", "| Rank | Site | Role | Score |", "|---|---|---|---|"]
        lines += [f"| {r} | {i} | {role} | {t} |" for r, i, role, t in s["top"]]
        lines += ["", f"Expected in the top half (rank ≤ {s['half']}) and present: "
                  + (", ".join(s["expected_met"]) or "none") + "."]
        if s["expected_missed"]:
            lines.append("Expected but lower: " + ", ".join(f"{i} (#{r})" for i, r in s["expected_missed"]) + ".")
        lines.append("All known analogs: " + ", ".join(
            f"{i} ({'excluded' if r is None else f'#{r}'}, {t})" for r, i, t in s["validation"]) + ".")
        lines.append("Best understudied sites: " + ", ".join(f"{n} ({t})" for _, n, t in s["top_candidates"]) + ".")
        if s["excluded"]:
            lines.append("Excluded by the bare-soil filter (NDVI > 0.2): " + ", ".join(s["excluded"]) + ".")
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
