"""Figure check (T50): every number quoted in the main docs is recomputed from the run summaries and catalogues.
A doc that drifts from the data fails here; a quoted figure that is removed from a doc must be removed here too."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

from science_grid import v3_indicators  # noqa: E402

V = v3_indicators()


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _mc(run, key):
    a, b = (int(x) for x in V["monte_carlo"][run][key].split("/"))
    return a, b


def _catalog_counts():
    import yaml
    return {b: len((yaml.safe_load(_read(f"data/catalog/{b}.yaml")) or {}).get("products", [])) for b in ("earth", "moon", "mars")}


def _millions(n):
    return f"{math.floor(n / 1e5 + 0.5) / 10:.1f} M"


def expected():
    moon, mars = V["cells"]["run-002"], V["cells"]["run-mars-001"]
    n_pol = _mc("run-mars-001", "D:mars-north-polar")[1] + _mc("run-mars-001", "D:mars-south-polar")[1]
    ice = _mc("run-mars-001", "D:mars-ice-rich-midlatitudes")
    mare = _mc("run-002", "B:moon-mare-plains")
    pits = _mc("run-002", "A:moon-pits")
    psr = _mc("run-002", "A:moon-psr")
    na, nb = V["nasadem"]["A"]["top_overlap"], V["nasadem"]["B"]["top_overlap"]
    ra, rb = V["resolution_30m"]["A"]["top_overlap"], V["resolution_30m"]["B"]["top_overlap"]
    plaus = sum(d.get("plausible", 0) for d in V["dossiers"].values())
    total = sum(sum(d.values()) for d in V["dossiers"].values())
    hidden = round(V["hidden_share"]["run-002"] * 100)
    s, c = V["sources"], _catalog_counts()
    masks = V["masks"]["run-002"].split("/")
    return {
        "readme.md": [f"{_millions(moon)} lunar and {_millions(mars)} Mars cells assessed",
                      V["positive_validation"].replace(" scenarios", "") + " scenarios with a positive validation",
                      f"{s['used']} sources"],
        "docs/VALIDATION.md": [f"No scenario has a positive validation ({V['positive_validation'].replace(' scenarios', '')})",
                               f"{masks[0]} of {masks[1]} negatives are masked or flagged",
                               f"only {na:.0%} (A) and {nb:.0%} (B) of the top 20",
                               f"{ra:.0%} and {rb:.0%} stay",
                               f"lunar pits {pits[0] / pits[1]:.0%}, permanently shadowed regions {psr[0] / psr[1]:.0%}",
                               f"Mars polar terrain 0 of {n_pol:,} zones",
                               f"lunar mare plains {mare[0] / mare[1]:.0%}, Mars ice-rich mid-latitudes {ice[0]:,} of {ice[1]:,}",
                               "fails for lunar pits** (KS 0.056",
                               f"Of {total} dossiers (lunar and Mars), {plaus} are plausible",
                               f"{hidden}% of lunar cells are half or more masked"],
        "docs/DATA.md": [f"{s['verified']} of {s['used']} are \"verified\"",
                         f"{c['earth']} Earth, {c['moon']} lunar and {c['mars']} Martian products"],
        "docs/LIMITS.md": [f"{na * 100:.0f} to {nb:.0%} of the top 20 lunar zones stay", f"{hidden}% of lunar cells"],
    }


@pytest.mark.parametrize("doc", sorted(expected()))
def test_quoted_figures_match_the_data(doc):
    text = _read(doc)
    missing = [f for f in expected()[doc] if f not in text]
    assert missing == [], f"{doc}: these figures are not in the doc, or differ from the data: {missing}"


def test_the_self_consistency_failure_quoted_is_the_one_in_the_run():
    v = json.loads(_read("data/runs/run-002/validation.json"))
    assert round(v["self_consistency"]["moon-pits"]["ks"], 3) == 0.056
