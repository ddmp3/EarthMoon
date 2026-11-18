"""Planetary environment specs of EarthMoon v3 (data/profiles/spec/*.yaml, task T20).

    python tools/profiles/profiles.py check        # validate every spec against the data catalogues

A spec says how an environment is selected from planetary data (never from Earth sites), which parameters are
available, at which scale, and what cannot be characterized. Values are computed later (T41 Moon, T48 Mars).
Rules checked here:
- every product is in the catalogue of the same body;
- a `ready` spec selects only with verified or partly verified products; a `conditional` one names its blockers;
- a threshold without a value carries a sensitivity grid (no arbitrary threshold);
- the selection does not use a parameter that is then compared (circular selection);
- a distribution keeps percentiles and the joint data, not a mean.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED = ("id", "body", "name", "kind", "status", "catalogue_environments", "selection", "parameters",
            "statistics", "biases", "cannot_characterize")
BODIES = ("moon", "mars")
KINDS = ("distribution", "site-set")
SPEC_STATUSES = ("ready", "conditional")
USABLE = ("verified", "partly verified")


DIMENSIONS = ("topography", "geology", "thermal", "hydric-ice", "environment", "operational")
COMPARABILITY = ("direct", "indirect", "process", "impossible", "model")
DECISIONS = ("keep", "merge", "drop", "context")
REDUNDANT = 0.8


def validate_parameters(params: list[dict], pairs: list[dict], ids: dict[str, dict[str, str]],
                        correlations: dict) -> list[str]:
    """Checks data/parameters.yaml. A kept pair with |Spearman| > 0.8 on any measured matrix needs a justification."""
    errors = []
    for p in params:
        name = p.get("id", "?")
        for f in ("id", "dimension", "definition", "unit", "scale", "sources", "comparability", "decision",
                  "reason", "does_not_measure"):
            if f not in p:
                errors.append(f"{name}: missing field {f}")
        if p.get("dimension") not in DIMENSIONS:
            errors.append(f"{name}: dimension must be one of {DIMENSIONS}")
        if p.get("comparability") not in COMPARABILITY:
            errors.append(f"{name}: comparability must be one of {COMPARABILITY}")
        if p.get("decision") not in DECISIONS:
            errors.append(f"{name}: decision must be one of {DECISIONS}")
        for body, products in (p.get("sources") or {}).items():
            for pid in products:
                if pid not in ids.get(body, {}):
                    errors.append(f"{name}: source {pid} is not in the {body} catalogue")
    kept = {p["id"] for p in params if p.get("decision") in ("keep", "merge")}
    justified = {frozenset(x["pair"]) for x in pairs if x.get("justification")}
    for label, block in correlations.items():
        keys = block["keys"]
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                v = block["spearman"][i][j]
                pair = frozenset((keys[i], keys[j]))
                if v is not None and abs(v) > REDUNDANT and pair <= kept and pair not in justified:
                    errors.append(f"{keys[i]}/{keys[j]}: |r| = {abs(v):.2f} on {label}, both kept, no justification")
    return errors


def validate_scenario(s: dict, ctx: dict, prefix: str = "") -> list[str]:
    """Checks a scenario (data/scenarios/*.yaml) or one instrument of scenario C.
    ctx: profiles (ids), parameters ({id: (decision, dimension)}), references (text of REFERENCES.md),
    experts (E ids of docs/LIMITS.md)."""
    name = prefix + s.get("id", "?")
    errors = [f"{name}: missing field {f}" for f in ("id", "name", "objective", "targets", "similarity", "context",
                                                     "requirements", "eliminating", "cannot_assess", "proxies")
              if f not in s]
    if errors:
        return errors
    for t in s["targets"]:
        if t not in ctx["profiles"]:
            errors.append(f"{name}: target profile {t} is not specified (T20)")
    for item in s["similarity"]:
        decision, dimension = ctx["parameters"].get(item.get("parameter"), (None, None))
        if decision != "keep" or dimension == "operational":
            errors.append(f"{name}: similarity parameter {item.get('parameter')} must be a kept, non-operational parameter")
    for p in s["context"]:
        if p not in ctx["parameters"]:
            errors.append(f"{name}: context parameter {p} is not in data/parameters.yaml")
    ids = set()
    for r in s["requirements"]:
        ids.add(r.get("id"))
        if not r.get("value"):
            errors.append(f"{name}: requirement {r.get('id')} needs a value")
        if r.get("source"):
            if r["source"] not in ctx["references"]:
                errors.append(f"{name}: source {r['source']} is not in docs/REFERENCES.md")
        elif r.get("expert_decision"):
            if r["expert_decision"] not in ctx["experts"]:
                errors.append(f"{name}: {r['expert_decision']} is not an expert decision of docs/LIMITS.md")
        else:
            errors.append(f"{name}: requirement {r.get('id')} needs a source or expert_decision")
    for e in s["eliminating"]:
        if e not in ids:
            errors.append(f"{name}: eliminating constraint {e} is not a requirement")
    if not s["cannot_assess"]:
        errors.append(f"{name}: cannot_assess cannot be empty")
    for p in s["proxies"]:
        for f in ("name", "stands_for", "why"):
            if not p.get(f):
                errors.append(f"{name}: proxy needs {f}")
    for inst in s.get("instruments", []):
        errors += validate_scenario(inst, ctx, prefix=name + "/")
    return errors


def catalogue_ids(catalog_dir: Path, bodies: tuple[str, ...] = BODIES) -> dict[str, dict[str, str]]:
    """{body: {product id: status}} from data/catalog/<body>.yaml."""
    out: dict[str, dict[str, str]] = {}
    for body in bodies:
        data = yaml.safe_load((Path(catalog_dir) / f"{body}.yaml").read_text(encoding="utf-8"))
        out[body] = {p["id"]: p["status"] for p in data["products"]}
    return out


def load_specs(spec_dir: Path) -> list[dict]:
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(Path(spec_dir).glob("*.yaml"))
            if p.name != "rejected.yaml"]


def validate_spec(s: dict, ids: dict[str, dict[str, str]]) -> list[str]:
    name = s.get("id", "?")
    errors = [f"{name}: missing field {f}" for f in REQUIRED if f not in s]
    if errors:
        return errors
    if s["body"] not in BODIES or not name.startswith(s["body"] + "-"):
        errors.append(f"{name}: body must be one of {BODIES} and prefix the id")
    if s["kind"] not in KINDS:
        errors.append(f"{name}: kind must be one of {KINDS}")
    if s["status"] not in SPEC_STATUSES:
        errors.append(f"{name}: status must be one of {SPEC_STATUSES}")
    known = ids.get(s["body"], {})
    sel = s["selection"]
    if not sel.get("rule") or not sel.get("steps"):
        errors.append(f"{name}: selection needs a rule and steps")
    products = [st.get("product") for st in sel.get("steps", [])] + [p.get("product") for p in s["parameters"]]
    for pid in products:
        if pid not in known:
            errors.append(f"{name}: product {pid} is not in the {s['body']} catalogue")
    unusable = sorted({st["product"] for st in sel.get("steps", [])
                       if st.get("product") in known and known[st["product"]] not in USABLE})
    if s["status"] == "ready" and unusable:
        errors.append(f"{name}: a ready spec selects with not verified products {unusable}")
    if s["status"] == "conditional" and not s.get("blocked_by"):
        errors.append(f"{name}: a conditional spec needs blocked_by")
    for p in sel.get("parameters", []):
        if not isinstance(p.get("value"), (int, float)) and not p.get("sensitivity"):
            errors.append(f"{name}: selection parameter {p.get('name')} has no value, so it needs a sensitivity grid")
    compared = {n for p in s["parameters"] for n in p.get("names", [])}
    for st in sel.get("steps", []):
        overlap = compared & set(st.get("uses", []))
        if overlap:
            errors.append(f"{name}: circular selection, {sorted(overlap)} selects and is compared")
    for p in s["parameters"]:
        for f in ("dimension", "names", "product", "scale", "effective_resolution"):
            if not p.get(f):
                errors.append(f"{name}: parameter entry needs {f}")
    stats = s["statistics"]
    if s["kind"] == "distribution" and (len(stats.get("percentiles", [])) < 5 or not stats.get("joint")):
        errors.append(f"{name}: a distribution needs at least 5 percentiles and the joint data")
    if not s["biases"]:
        errors.append(f"{name}: biases cannot be empty")
    return errors


def validate_rejected(entries: list[dict]) -> list[str]:
    return [f"{e.get('id', '?')}: rejected entry needs {f}" for e in entries for f in ("id", "body", "reason")
            if not e.get(f)]


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    spec_dir = root / "data" / "profiles" / "spec"
    ids = catalogue_ids(root / "data" / "catalog")
    specs = load_specs(spec_dir)
    errors = [e for s in specs for e in validate_spec(s, ids)]
    errors += validate_rejected(yaml.safe_load((spec_dir / "rejected.yaml").read_text(encoding="utf-8"))["rejected"])
    params = yaml.safe_load((root / "data" / "parameters.yaml").read_text(encoding="utf-8"))
    import json
    corr = json.loads((root / "data" / "research" / "redundancy-t21.json").read_text(encoding="utf-8"))["matrices"]
    all_ids = catalogue_ids(root / "data" / "catalog", bodies=("earth", "moon", "mars"))
    errors += validate_parameters(params["parameters"], params.get("pairs", []), all_ids, corr)
    import re
    ctx = {"profiles": {s["id"] for s in specs},
           "parameters": {p["id"]: (p["decision"], p["dimension"]) for p in params["parameters"]},
           "references": (root / "docs" / "REFERENCES.md").read_text(encoding="utf-8"),
           "experts": set(re.findall(r"^\| (E\d+) \|", (root / "docs" / "LIMITS.md").read_text(encoding="utf-8"), re.M))}
    scenarios = sorted((root / "data" / "scenarios").glob("*.yaml"))
    for path in scenarios:
        errors += validate_scenario(yaml.safe_load(path.read_text(encoding="utf-8")), ctx)
    for e in errors:
        print(e)
    print(f"{len(specs)} specs, {len(params['parameters'])} parameters, {len(scenarios)} scenarios, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
