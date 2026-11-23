"""Internal discovery service (ADR-005): only the Node API calls it, on the Compose network. No public port, no
outbound network, read-only data.

    RELEASES_DIR=/data/releases uvicorn app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, HTTPException, Query

from core import QueryError, Release, cells_at, cells_in_bbox, run_query

ROOT = Path(os.environ.get("RELEASES_DIR", "/data/releases"))
_RELEASES: dict[str, Release] = {}


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    preload()
    yield


app = FastAPI(title="EarthMoon discovery (internal)", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan)


def _release(rid: str | None) -> Release:
    """The current release, or one listed in index.json. Ids come from the index, never from the path given."""
    index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    rid = rid or index["current"]
    listed = {r["id"] for r in index["releases"]}
    for old in [k for k in _RELEASES if k not in listed]:      # dropped after a switch by the refresher (T52)
        del _RELEASES[old]
    if rid not in listed:
        raise HTTPException(404, f"Unknown release: {rid[:40]}")
    if rid not in _RELEASES:
        scen = json.loads((ROOT / rid / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
        targets = sorted({t for s in scen for t in s["assessed_targets"]})
        _RELEASES[rid] = Release(ROOT / rid, targets)
    return _RELEASES[rid]


def preload() -> None:
    """Load the current release, and the current release of each body, before the first request: reading 6 M cells
    takes several seconds."""
    if (ROOT / "index.json").exists():
        _release(None)
        index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
        for rid in (index.get("current_by_body") or {}).values():
            _release(rid)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cells")
def cells(bbox: str = Query(..., max_length=100), env: str = Query(..., max_length=60),
          release: str | None = Query(None, max_length=20)) -> dict:
    try:
        box = [float(v) for v in bbox.split(",")]
    except ValueError as e:
        raise HTTPException(400, "bbox must be west,south,east,north in degrees") from e
    try:
        return cells_in_bbox(_release(release), box, env)
    except QueryError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/query")
def query(q: dict = Body(...), release: str | None = Query(None, max_length=20)) -> dict:
    try:
        return run_query(_release(release), q)
    except QueryError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/points")
def points(body: dict = Body(...), release: str | None = Query(None, max_length=20)) -> dict:
    """Values at named points (the known sites of the missions), for the given environments."""
    try:
        envs = body.get("envs")
        if not isinstance(envs, list) or not envs:
            raise QueryError("envs must be a non-empty list")
        return cells_at(_release(release), body.get("points"), envs)
    except QueryError as e:
        raise HTTPException(400, str(e)) from e
