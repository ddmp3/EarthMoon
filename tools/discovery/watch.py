"""Source watchers of the refresher (T52 step 2, ADR-009 section 1).

Each watched source has a `refresh` block in the catalogue (`data/catalog/*.yaml`). Its `watch` targets say what the
watcher reads; the watcher turns the answer into a signal, `{item: {field: value}}`, and compares it with the previous
one. It never assumes a source is unchanged:
- no previous signal and nothing recorded at ingest: `baseline` (the signal is stored, no claim is made);
- an unreachable source, a refusal, a server error or a pattern that no longer matches: `check_failed`;
- an item that the source no longer lists (404, 410, or absent from a listing): `withdrawn`;
- any field that differs, or a new item in a listing: `changed`;
- otherwise `unchanged`.
Families without a usable signal (`none`, `cds`, or no `watch` target recorded) are `not_checkable`.

Every request goes through `make_fetch`, which refuses hosts that are not catalogue watch targets.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable
from xml.etree import ElementTree

USER_AGENT = "earthmoon-research/1.0"
DATACITE = "https://api.datacite.org/dois/"


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""


class FetchError(Exception):
    """The source could not be reached (network, timeout, or a host outside the catalogue)."""


class CheckFailed(Exception):
    """The source answered, but not with a usable signal."""


class NotCheckable(Exception):
    """The source has no usable machine signal."""


Fetch = Callable[..., Response]


def make_fetch(allowed_hosts: set[str], timeout: float = 60.0) -> Fetch:
    """The only way the refresher reaches the network: catalogue hosts only, generic User-Agent, no credentials."""
    def fetch(url: str, method: str = "GET") -> Response:
        host = urllib.parse.urlsplit(url).hostname or ""
        if host not in allowed_hosts:
            raise FetchError(f"not a catalogue host: {host}")
        req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (host checked above)
                return Response(r.status, {k: v for k, v in r.headers.items()}, r.read() if method != "HEAD" else b"")
        except urllib.error.HTTPError as e:
            return Response(e.code, dict(e.headers or {}), b"")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise FetchError(f"unreachable: {url} ({e})") from e
    return fetch


def catalogue_hosts(entries: list[dict]) -> set[str]:
    """Hosts the refresher may reach: those of the watch targets of every catalogue entry."""
    hosts = set()
    for e in entries:
        w = (e.get("refresh") or {}).get("watch") or {}
        if "doi" in w:
            hosts.add(urllib.parse.urlsplit(DATACITE).hostname)
        for k in ("bucket", "base", "url", "endpoint"):
            if w.get(k):
                hosts.add(urllib.parse.urlsplit(w[k]).hostname)
    hosts.discard(None)
    return hosts


def _ok(r: Response, url: str) -> Response:
    if r.status != 200:
        raise CheckFailed(f"HTTP {r.status} from {url}")
    return r


def _header(r: Response, name: str):
    for k, v in r.headers.items():
        if k.lower() == name.lower():
            return v
    return None


def _s3(w: dict, fetch: Fetch) -> tuple[dict, dict | None]:
    """ListObjectsV2 of a public bucket, every page; items are the keys that match `match`."""
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    base = w["bucket"].rstrip("/") + "/?list-type=2" + (f"&prefix={urllib.parse.quote(w['prefix'])}" if w.get("prefix") else "")
    pat = re.compile(w.get("match") or ".")
    out, token = {}, None
    while True:
        url = base + (f"&continuation-token={urllib.parse.quote(token)}" if token else "")
        root = ElementTree.fromstring(_ok(fetch(url), url).body)
        q = (lambda t: f"s:{t}") if root.tag.startswith("{") else (lambda t: t)  # noqa: E731
        for c in root.findall(q("Contents"), ns):
            key = c.findtext(q("Key"), namespaces=ns)
            if key and pat.search(key):
                out[key] = {"etag": (c.findtext(q("ETag"), namespaces=ns) or "").strip('"'),
                            "size": int(c.findtext(q("Size"), namespaces=ns) or 0)}
        if (root.findtext(q("IsTruncated"), namespaces=ns) or "false") != "true":
            return out, None
        token = root.findtext(q("NextContinuationToken"), namespaces=ns)


def _pds(w: dict, fetch: Fetch) -> tuple[dict, dict | None]:
    """HEAD of each file used; the ingest size is the baseline of a first check."""
    out, ingest = {}, {}
    for name, size in (w.get("files") or {}).items():
        url = w["base"] + name
        r = fetch(url, method="HEAD")
        if size is not None:
            ingest[name] = {"size": int(size)}
        if r.status in (404, 410):
            continue
        _ok(r, url)
        n = _header(r, "Content-Length")
        out[name] = {"size": int(n) if n is not None else None, "etag": _header(r, "ETag"),
                     "last_modified": _header(r, "Last-Modified")}
    return out, (ingest or None)


def _page(w: dict, fetch: Fetch) -> tuple[dict, dict | None]:
    r = _ok(fetch(w["url"]), w["url"])
    found = re.findall(w["pattern"], r.body.decode("utf-8", "replace"))
    if not found:
        raise CheckFailed(f"the pattern no longer matches the page {w['url']}")
    return {f"match-{i}": {"value": v} for i, v in enumerate(found)}, None


def _doi(w: dict, fetch: Fetch) -> tuple[dict, dict | None]:
    url = DATACITE + w["doi"]
    r = fetch(url)
    if r.status in (404, 410):
        return {}, None
    a = json.loads(_ok(r, url).body)["data"]["attributes"]
    upd = [d.get("date") for d in a.get("dates") or [] if d.get("dateType") == "Updated"]
    return {w["doi"]: {"version": a.get("version"), "updated": max(upd) if upd else None}}, None


def _api(w: dict, fetch: Fetch) -> tuple[dict, dict | None]:
    r = _ok(fetch(w["endpoint"]), w["endpoint"])
    v = json.loads(r.body)
    try:
        for part in w["path"].split("."):
            v = v[int(part)] if isinstance(v, list) else v[part]
    except (KeyError, IndexError, ValueError, TypeError) as e:
        raise CheckFailed(f"no value at {w['path']} in {w['endpoint']}") from e
    return {"value": {"value": v}}, None


HANDLERS = {"s3": _s3, "pds": _pds, "page": _page, "doi": _doi, "api": _api, "cmr": _api}


def compare(prev: dict, new: dict, listing: bool) -> dict:
    """Items withdrawn, changed (a shared field differs) and added (new items count as a change in a listing)."""
    withdrawn = sorted(k for k in prev if k not in new)
    changed = sorted(k for k in prev if k in new and any(
        new[k].get(f) is not None and new[k][f] != prev[k][f]       # a field the source stops sending is no change
        for f in prev[k]))
    added = sorted(k for k in new if k not in prev) if listing else []
    state = "withdrawn" if withdrawn else ("changed" if changed or added else "unchanged")
    return {"state": state, "withdrawn": withdrawn, "changed": changed, "added": added}


def check(source: str, refresh: dict, previous: dict | None, fetch: Fetch, now: str) -> dict:
    """One check of one source. `previous` is the last stored signal (None on the first check)."""
    out = {"id": source, "checked_at": now, "family": refresh.get("family"), "signal": None,
           "withdrawn": [], "changed": [], "added": [], "reason": None}
    fam, w = refresh.get("family"), refresh.get("watch")
    try:
        if fam == "none":
            raise NotCheckable("no machine signal at the source")
        if fam == "cds":
            raise NotCheckable("no CDS watcher yet: no release uses a CDS source, and CDS needs the local key")
        if not w:
            raise NotCheckable("no target recorded at ingest for this source")
        signal, ingest = HANDLERS[fam](w, fetch)
    except NotCheckable as e:
        return {**out, "state": "not_checkable", "reason": str(e)}
    except (FetchError, CheckFailed, ElementTree.ParseError, json.JSONDecodeError, KeyError) as e:
        return {**out, "state": "check_failed", "reason": str(e)}
    out["signal"] = signal
    base = previous if previous is not None else ingest
    if base is None:
        return {**out, "state": "baseline"}
    return {**out, **compare(base, signal, listing=fam == "s3")}
