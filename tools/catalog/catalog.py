"""Data catalogues of EarthMoon v3 (data/catalog/moon.yaml, mars.yaml, earth.yaml).

    python tools/catalog/catalog.py check                         # validate every catalogue
    python tools/catalog/catalog.py render data/catalog/moon.yaml docs/wiki/data/moon-table.md "Lunar data catalogue"

One entry per data product. A fact is written only if it was read at its source (verified_url, verified_on);
otherwise the entry says "not verified". `nature` separates measurements from derived products, model
output and interpretations (docs/plan/tasks/T10-moon-data.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

NATURES = ("measured", "derived", "model", "interpretation")
STATUSES = ("verified", "partly verified", "not verified", "not available")
REQUIRED = (
    "id", "body", "mission", "instrument", "product", "producer", "url", "access", "coverage",
    "resolution_spatial", "resolution_effective", "resolution_temporal", "units", "nature", "uncertainty",
    "limitations", "dimensions", "environments", "status", "verified_on", "verified_url",
)
ACCESS = ("format", "size", "licence", "account")
# Earth layers: what each one is used for (T12). Similarity = compared with a planetary property;
# mask = excludes or delimits areas (water, ice, vegetation); qualification = explains or flags a result;
# operations = suitability for a test (access, logistics), never similarity.
USES = ("similarity", "mask", "qualification", "operations")


def load(path: Path) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data.get("products", [])


def validate(entries: list[dict]) -> list[str]:
    errors, seen = [], set()
    for i, e in enumerate(entries):
        name = e.get("id", f"#{i}")
        for field in REQUIRED:
            if field not in e:
                errors.append(f"{name}: missing field {field}")
        if name in seen:
            errors.append(f"{name}: duplicate id")
        seen.add(name)
        if e.get("nature") not in NATURES:
            errors.append(f"{name}: nature must be one of {NATURES}")
        if e.get("status") not in STATUSES:
            errors.append(f"{name}: status must be one of {STATUSES}")
        if e.get("status") in ("verified", "partly verified") and not (e.get("verified_on") and e.get("verified_url")):
            errors.append(f"{name}: a verified entry needs verified_on and verified_url")
        access = e.get("access")
        if not isinstance(access, dict) or any(k not in access for k in ACCESS):
            errors.append(f"{name}: access needs {ACCESS}")
        if e.get("body") == "earth":
            if not e.get("attribution"):
                errors.append(f"{name}: an Earth entry needs attribution (licence and credit text)")
            uses = e.get("use")
            if not isinstance(uses, list) or not uses or any(u not in USES for u in uses):
                errors.append(f"{name}: use must be a non-empty list from {USES}")
        for field in ("dimensions", "environments"):
            if field in e and not isinstance(e[field], list):
                errors.append(f"{name}: {field} must be a list")
        if "refresh" in e:
            errors += [f"{name}: {err}" for err in validate_refresh(e["refresh"])]
    return errors


# T52 (ADR-009, section 1): how the refresher watches a source. `family` is the kind of machine signal; `none` means
# no signal exists, so the source is reported `not_checkable` and never `up_to_date`. The cadence is the one stated at
# its source page (`checked_url`, `checked_on`), or "not verified".
REFRESH_FAMILIES = ("s3", "cmr", "cds", "pds", "doi", "page", "api", "none")
REFRESH_INTERVALS = ("daily", "weekly", "monthly", "none")


def validate_refresh(r) -> list[str]:
    if not isinstance(r, dict):
        return ["refresh must be a mapping"]
    errs = []
    if r.get("family") not in REFRESH_FAMILIES:
        errs.append(f"refresh family must be one of {REFRESH_FAMILIES}")
    if r.get("interval") not in REFRESH_INTERVALS:
        errs.append(f"refresh interval must be one of {REFRESH_INTERVALS}")
    if (r.get("family") == "none") != (r.get("interval") == "none"):
        errs.append("refresh family none and interval none go together (no signal, not checkable)")
    if r.get("family") != "none" and not r.get("signal"):
        errs.append("refresh signal is required when the source is checked")
    if not r.get("cadence"):
        errs.append("refresh cadence is required (quote the page, or write 'not stated on page')")
    if r.get("cadence_status") not in ("verified", "not verified"):
        errs.append("refresh cadence_status must be verified or not verified")
    elif r["cadence_status"] == "verified" and not (r.get("checked_url") and r.get("checked_on")):
        errs.append("a verified refresh cadence needs checked_url and checked_on")
    w = r.get("watch")
    if w is not None:
        need = WATCH_KEYS.get(r.get("family"), ())
        if not isinstance(w, dict) or not need:
            errs.append(f"refresh watch is not used by family {r.get('family')}")
        else:
            errs += [f"refresh watch for {r['family']} needs {k}" for k in need if not w.get(k)]
    return errs


# What the watcher of each family reads (tools/discovery/watch.py). No watch: the source is not checkable yet.
WATCH_KEYS = {"s3": ("bucket",), "pds": ("base", "files"), "page": ("url", "pattern"), "doi": ("doi",),
              "api": ("endpoint", "path"), "cmr": ("endpoint", "path")}


def _cell(value) -> str:
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return str(value if value is not None else "").replace("|", "/").replace("\n", " ")


def render_markdown(entries: list[dict], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        "Generated from the YAML catalogue by `tools/catalog/catalog.py render`. Do not edit by hand.",
        "",
        "| Product | Mission / instrument | Nature | Coverage | Resolution (pixel / effective) | Units | Uncertainty | Limitations | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        product = f"[{_cell(e['product'])}]({e['url']})" if e.get("url") else _cell(e["product"])
        lines.append(
            f"| {product} | {_cell(e['mission'])} {_cell(e['instrument'])} | {_cell(e['nature'])} | {_cell(e['coverage'])} "
            f"| {_cell(e['resolution_spatial'])} / {_cell(e['resolution_effective'])} | {_cell(e['units'])} "
            f"| {_cell(e['uncertainty'])} | {_cell(e['limitations'])} | {_cell(e['status'])} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    if argv[:1] == ["check"]:
        bad = 0
        for path in sorted((root / "data" / "catalog").glob("*.yaml")):
            errs = validate(load(path))
            for err in errs:
                print(f"{path.name}: {err}")
            bad += len(errs)
            print(f"{path.name}: {len(load(path))} products, {len(errs)} errors")
        return 1 if bad else 0
    if argv[:1] == ["render"] and len(argv) == 4:
        Path(argv[2]).write_text(render_markdown(load(Path(argv[1])), argv[3]), encoding="utf-8")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
