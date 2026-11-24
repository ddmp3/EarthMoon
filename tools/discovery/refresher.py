"""Refresher: checks the sources when due and writes what users see about freshness (T52 step 5, ADR-009).

State per source (`/data/refresh/state.json`, refresher only):
- `release_signal`: the signal the served release was built from. Every check compares with it, so a change stays
  detected until a published release uses it (`consumed`).
- the first check has no such base: its signal becomes the base and the state is `first_check` (changes between the
  ingest and that check are not known; nothing claims "up to date" yet).

Public file (`<releases>/freshness.json`, read by `GET /api/v3/status`): one entry per source with its state, last
check, last success and check interval. The API derives `check_overdue` (last check older than twice the interval)
and `newer_release`, so a stopped refresher shows as overdue.

    PYTHONPATH=tools python -m discovery.refresher check --state /data/refresh/state.json --releases /data/releases
    (loop: the same every --every-min minutes; each source is still checked only when its interval is due)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from discovery.watch import check

INTERVAL_HOURS = {"daily": 24, "weekly": 168, "monthly": 720, "none": None}


def _t(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def update_entry(entry: dict | None, res: dict) -> dict:
    e = dict(entry or {"release_signal": None, "last_success": None, "detected_on": None})
    e.update({"last_check": res["checked_at"], "reason": res.get("reason")})
    st = res["state"]
    if st in ("check_failed", "not_checkable"):
        e["state"] = st
        return e
    e["last_success"] = res["checked_at"]
    if st == "baseline":
        e.update(state="first_check", release_signal=res["signal"])
    elif st == "unchanged":
        e.update(state="up_to_date", detected_on=None)
        if e.get("release_signal") is None:                   # first check, equal to the ingest: keep the full signal
            e["release_signal"] = res["signal"]
    else:                                                     # changed or withdrawn
        if e.get("release_signal") is None:                   # first check, against the ingest: the ingest stays the base
            e["release_signal"] = res.get("base")
        e.update(state="update_detected", detected_on=e.get("detected_on") or res["checked_at"],
                 changed=res.get("changed", []), withdrawn=res.get("withdrawn", []), added=res.get("added", []))
    return e


def consumed(entry: dict, signal: dict) -> dict:
    """A published release was built from `signal`: it becomes the comparison base."""
    return {**entry, "release_signal": signal, "state": "up_to_date", "detected_on": None,
            "changed": [], "withdrawn": [], "added": []}


def due(entry: dict | None, interval: str, now: str) -> bool:
    hours = INTERVAL_HOURS.get(interval)
    if entry is None:
        return True
    if hours is None:
        return False
    return (_t(now) - _t(entry["last_check"])).total_seconds() >= hours * 3600


def freshness(entries: dict, intervals: dict, progress: dict | None, held: list, now: str,
              new_products: list | None = None, impact: list | None = None) -> dict:
    running = set((progress or {}).get("sources", []))
    waiting = {s for h in held for s in h.get("sources", [])}
    out = {}
    for sid, e in sorted(entries.items()):
        state = e["state"]
        if state == "update_detected" and sid in running:
            state = "update_in_progress"
        elif state == "update_detected" and sid in waiting:
            state = "update_held"
        out[sid] = {"state": state, "last_check": e.get("last_check"), "last_success": e.get("last_success"),
                    "detected_on": e.get("detected_on"), "reason": e.get("reason"),
                    "interval_hours": INTERVAL_HOURS.get(intervals.get(sid, "none"))}
    return {"refresher": True, "written_at": now, "sources": out, "progress": progress, "held": held,
            "new_products": new_products or [], "impact": impact or []}


def served_releases(idx: dict) -> list[dict]:
    """The current release of each body; an index written before bodies existed has the lunar one as `current`."""
    by = dict(idx.get("current_by_body") or {})
    if idx.get("current") and "moon" not in by:
        by["moon"] = idx["current"]
    return [{"id": rid, "body": body} for body, rid in sorted(by.items())]


def impacts(entries: dict, rels: list[dict]) -> list[dict]:
    """Pre-analysis of every detected update (T52b): never starts a recompute."""
    from discovery.impact import impact
    return [impact(sid, e, rels) for sid, e in sorted(entries.items()) if e.get("state") == "update_detected"]


def _write_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_checks(catalog: list[dict], store: Path, fetch, now: str) -> dict:
    """Check every watched source that is due; store the new state. Returns the state."""
    state = json.loads(store.read_text()) if store.exists() else {"entries": {}}
    state.setdefault("new_products", [])
    state.setdefault("release_tables", {})
    for e in catalog:
        r = e.get("refresh")
        if not r:
            continue
        _new_products(e["id"], r.get("new_products"), state, fetch, now)
        cur = state["entries"].get(e["id"])
        if not due(cur, r.get("interval", "none"), now) and cur is not None:
            continue
        res = check(e["id"], r, (cur or {}).get("release_signal"), fetch, now)
        state["entries"][e["id"]] = update_entry(cur, res)
    state["checked_at"] = now
    _write_atomic(store, state)
    return state


def _new_products(sid: str, np_cfg: dict | None, state: dict, fetch, now: str) -> None:
    """New planetary products (T52, David 23/11): a release table read with its pattern. New entries are logged
    "detected, to verify", never used: a new reference is a new protocol version, decided before any run."""
    if not np_cfg:
        return
    seen = state["release_tables"].get(sid)
    if seen is not None and not due({"last_check": seen["checked_at"]}, np_cfg.get("interval", "weekly"), now):
        return
    res = check(sid, {"family": "page", "watch": {"url": np_cfg["url"], "pattern": np_cfg["pattern"]}}, None, fetch, now)
    if res["state"] != "baseline":
        return                                                # unreachable or pattern lost: retried next time
    found = sorted({v["value"] for v in res["signal"].values()})
    if seen is not None:
        for f in found:
            if f not in seen["found"]:
                state["new_products"].append({"source": sid, "found": f, "detected_on": now,
                                              "status": "detected, to verify", "url": np_cfg["url"]})
    state["release_tables"][sid] = {"found": sorted(set(found) | set((seen or {}).get("found", []))), "checked_at": now}


def load_catalog(root: Path) -> list[dict]:
    import yaml
    out = []
    for p in sorted((root / "data" / "catalog").glob("*.yaml")):
        out += (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("products", [])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["check", "loop"])
    ap.add_argument("--state", type=Path, default=Path("/data/refresh/state.json"))
    ap.add_argument("--releases", type=Path, default=Path("/data/releases"))
    ap.add_argument("--every-min", type=float, default=60.0)
    a = ap.parse_args(argv)
    if not (a.releases / "index.json").exists():
        print(f"no releases in {a.releases}: set EARTHMOON_DATA to the data folder", file=sys.stderr)
        return 2
    while True:
        once(a.state, a.releases)
        if a.what == "check":
            return 0
        import time
        time.sleep(a.every_min * 60)


def once(state_path: Path, releases: Path) -> None:
    from discovery.watch import catalogue_hosts, make_fetch
    root = Path(__file__).resolve().parents[2]
    catalog = [e for e in load_catalog(root) if e.get("refresh")]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = run_checks(catalog, state_path, make_fetch(catalogue_hosts(catalog)), now)
    idx_path = releases / "index.json"
    idx = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    held = idx.get("held", [])
    intervals = {e["id"]: e["refresh"].get("interval", "none") for e in catalog}
    from discovery.impact import releases as release_views
    served = served_releases(idx)
    imp = impacts(state["entries"], release_views(releases, served)) if served else []
    _write_atomic(releases / "freshness.json", freshness(state["entries"], intervals, state.get("progress"), held, now,
                                                        new_products=state.get("new_products"), impact=imp))
    for sid, e in sorted(state["entries"].items()):
        print(f"{now} {sid}: {e['state']}{' (' + e['reason'] + ')' if e.get('reason') else ''}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
