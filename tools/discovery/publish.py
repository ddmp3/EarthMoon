"""Automatic publication of a refreshed release (T52 step 4, ADR-009 section 3).

A refreshed release is built next to the served ones, then published only if:
- the validation protocol passes (every check);
- the regression anchor holds (lunar: the v2 south polar cap keeps 71,731 windows within 1%; Mars has no anchor, so
  every Mars release waits for review);
- less than 1% of evaluated cells change state, and no zone appears or disappears.
Otherwise it is held, with its reasons, and David approves or rejects it:

    PYTHONPATH=tools python -m discovery.publish approve|reject <release id> --releases /data/releases
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

CHANGE_THRESHOLD = 0.01                # proposed in ADR-009, calibrated in T52 step 7
ANCHOR = {"profile": "moon-south-polar-cap-v2", "windows": 71731, "tolerance": 0.01}


class PublishError(Exception):
    """A publication request that cannot apply (unknown or not held release)."""


def anchor(profiles: list[dict], body: str) -> dict | None:
    """Regression anchor of a body; None when the body has none."""
    if body != "moon":
        return None
    p = next((p for p in profiles if p.get("id") == ANCHOR["profile"]), None)
    n = ((p or {}).get("windows") or {}).get("valid")
    if n is None:
        return {"pass": False, "detail": f"profile {ANCHOR['profile']} missing"}
    ok = abs(n - ANCHOR["windows"]) <= ANCHOR["tolerance"] * ANCHOR["windows"]
    return {"pass": ok, "detail": f"{n:,} windows against {ANCHOR['windows']:,} (tolerance 1%)"}


def state_change(old: dict, new: dict) -> float:
    """Share of the cells evaluated in either release whose state differs (a cell absent from one counts as changed)."""
    ev = {c for c, s in old.items() if s == "evaluated"} | {c for c, s in new.items() if s == "evaluated"}
    if not ev:
        return 0.0
    return sum(old.get(c) != new.get(c) for c in ev) / len(ev)


def zone_change(old: list[dict], new: list[dict]) -> tuple[int, int]:
    """Zones that appear and disappear; a zone is its target and its set of cells."""
    key = lambda z: (z.get("target"), frozenset(z.get("cell_ids") or []))  # noqa: E731
    a, b = {key(z) for z in old}, {key(z) for z in new}
    return len(b - a), len(a - b)


def gate(validity: dict, anch: dict | None, change: dict, threshold: float = CHANGE_THRESHOLD) -> dict:
    reasons = []
    if validity.get("state") != "validated":
        failing = [c["check"] for c in validity.get("checks", []) if c.get("pass") is not True]
        reasons.append(f"validation: not validated (failing: {', '.join(failing) or 'unknown'})")
    if anch is None:
        reasons.append("no regression anchor for this body")
    elif anch.get("pass") is not True:
        reasons.append(f"regression anchor fails: {anch.get('detail', '')}")
    share = change.get("cells_changed_share", 0.0)
    if share >= threshold:
        reasons.append(f"{share * 100:.1f}% of evaluated cells change state (threshold {threshold * 100:.0f}%)")
    if change.get("zones_appeared"):
        n = change["zones_appeared"]
        reasons.append(f"{n} zone{' appears' if n == 1 else 's appear'}")
    if change.get("zones_disappeared"):
        n = change["zones_disappeared"]
        reasons.append(f"{n} zone{' disappears' if n == 1 else 's disappear'}")
    return {"publish": not reasons, "reasons": reasons}


def _write_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _switch(idx: dict, entry: dict) -> None:
    from discovery.release import keep_releases
    entry = {k: v for k, v in entry.items() if k != "reasons"}
    idx["releases"] = keep_releases(idx.get("releases", []), entry)
    body = entry.get("body", "moon")
    idx.setdefault("current_by_body", {})[body] = entry["id"]
    if body == "moon" or "current" not in idx:
        idx["current"] = entry["id"]                          # the default release stays lunar


def register(index_path: Path, entry: dict, decision: dict) -> None:
    """Publish the release (atomic switch of the index) or hold it with its reasons."""
    idx = json.loads(Path(index_path).read_text())
    ch = Path(index_path).parent / entry["id"] / "changes.json"        # the decision, for researchers (T52)
    if ch.exists():
        doc = json.loads(ch.read_text())
        doc["decision"] = decision
        _write_atomic(ch, doc)
    if decision["publish"]:
        _switch(idx, entry)
    else:
        idx["held"] = [h for h in idx.get("held", []) if h["id"] != entry["id"]] + [
            {**entry, "reasons": decision["reasons"]}]
    _write_atomic(Path(index_path), idx)


def _held(idx: dict, rid: str) -> dict:
    h = next((h for h in idx.get("held", []) if h["id"] == rid), None)
    if h is None:
        raise PublishError(f"{rid} is not held for review")
    return h


def approve(index_path: Path, rid: str) -> None:
    idx = json.loads(Path(index_path).read_text())
    h = _held(idx, rid)
    idx["held"] = [x for x in idx["held"] if x["id"] != rid]
    _switch(idx, h)
    _write_atomic(Path(index_path), idx)


def reject(index_path: Path, rid: str) -> None:
    """Remove a held release and its files. A served release is never touched."""
    idx = json.loads(Path(index_path).read_text())
    _held(idx, rid)
    idx["held"] = [x for x in idx["held"] if x["id"] != rid]
    _write_atomic(Path(index_path), idx)
    d = Path(index_path).parent / rid
    if d.is_dir():
        shutil.rmtree(d)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def share_unchanged(new: Path, old: Path) -> int:
    """Replace every file of `new` identical to the same path in `old` by a hard link; returns how many."""
    n = 0
    for f in new.rglob("*"):
        o = old / f.relative_to(new)
        if f.is_file() and o.is_file() and f.stat().st_size == o.stat().st_size and _sha(f) == _sha(o):
            tmp = f.with_name(f.name + ".link")
            try:
                os.link(o, tmp)
            except OSError:
                continue                                       # no hard links on this volume: keep the copy
            os.replace(tmp, f)
            n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["approve", "reject"])
    ap.add_argument("release")
    ap.add_argument("--releases", type=Path, default=Path("/data/releases"))
    a = ap.parse_args(argv)
    try:
        (approve if a.action == "approve" else reject)(a.releases / "index.json", a.release)
    except PublishError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"{a.action}d {a.release}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
