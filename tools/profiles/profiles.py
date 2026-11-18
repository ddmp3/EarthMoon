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


def catalogue_ids(catalog_dir: Path) -> dict[str, dict[str, str]]:
    """{body: {product id: status}} from data/catalog/<body>.yaml."""
    out: dict[str, dict[str, str]] = {}
    for body in BODIES:
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
    for e in errors:
        print(e)
    print(f"{len(specs)} specs, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
