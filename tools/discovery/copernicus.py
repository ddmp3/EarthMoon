"""Copernicus DEM on AWS (catalogue ids copernicus-dem-glo30, copernicus-dem-glo90).

Tile names carry no release code (bucket readme, read 18/11/2026), so a tile is identified by its S3 key and its
change signal: ETag, size and LastModified from the anonymous ListObjectsV2 listing.
"""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

PRODUCTS = {
    "glo30": {"catalogue": "copernicus-dem-glo30", "bucket": "https://copernicus-dem-30m.s3.amazonaws.com", "code": "10"},
    "glo90": {"catalogue": "copernicus-dem-glo90", "bucket": "https://copernicus-dem-90m.s3.amazonaws.com", "code": "30"},
}
_KEY = re.compile(r"Copernicus_DSM_COG_\d+_([NS])(\d{2})_00_([EW])(\d{3})_00_DEM/Copernicus_DSM_COG_\d+_[NS]\d{2}_00_[EW]\d{3}_00_DEM\.tif$")
_CONTENTS = re.compile(r"<Contents>(.*?)</Contents>", re.S)


def _field(name: str, text: str) -> str | None:
    m = re.search(rf"<{name}>(.*?)</{name}>", text, re.S)
    return m.group(1) if m else None


def tile_name(lat: int, lon: int, product: str) -> str:
    ns, ew = ("N" if lat >= 0 else "S"), ("E" if lon >= 0 else "W")
    return f"Copernicus_DSM_COG_{PRODUCTS[product]['code']}_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"


def tile_key(lat: int, lon: int, product: str) -> str:
    name = tile_name(lat, lon, product)
    return f"{name}/{name}.tif"


def tile_url(lat: int, lon: int, product: str) -> str:
    return f"{PRODUCTS[product]['bucket']}/{tile_key(lat, lon, product)}"


def s3_objects(xml: str) -> tuple[list[dict], str | None]:
    """Objects of one anonymous S3 ListObjectsV2 page (key and change signal), and the continuation token."""
    objs = [{"key": _field("Key", b) or "", "etag": html.unescape(_field("ETag", b) or "").strip('"'),
             "size": int(_field("Size", b) or 0), "last_modified": _field("LastModified", b)}
            for b in _CONTENTS.findall(xml)]
    return objs, _field("NextContinuationToken", xml)


def s3_list(bucket: str, prefix: str = "", timeout: int = 60) -> list[dict]:
    """Every object of a public bucket under `prefix` (network)."""
    out, token = [], None
    while True:
        url = f"{bucket}/?list-type=2&prefix={urllib.parse.quote(prefix)}" + (
            f"&continuation-token={urllib.parse.quote(token)}" if token else "")
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            page, token = s3_objects(resp.read().decode())
        out += page
        if not token:
            return out


def _by_tile(objs: list[dict]) -> dict:
    out = {}
    for o in objs:
        m = _KEY.search(o["key"])
        if m:
            lat = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
            lon = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
            out[(lat, lon)] = o
    return out


def parse_listing(xml: str) -> tuple[dict, str | None]:
    """DEM GeoTIFFs of one listing page, keyed by tile (south-west corner), and the continuation token."""
    objs, token = s3_objects(xml)
    return _by_tile(objs), token


def list_tiles(product: str) -> dict:
    """Every DEM tile of the bucket with its change signal (network: anonymous S3 listing, about 5 min)."""
    return _by_tile(s3_list(PRODUCTS[product]["bucket"]))


def local_copy(lat: int, lon: int, product: str, cache, signal: dict) -> tuple:
    """Download a tile once into `cache`, with its SHA-256. Kept while its ETag and size match the listing,
    downloaded again otherwise (a changed tile, ADR-009). Not safe for two writers of the same tile."""
    import hashlib
    import json
    from pathlib import Path
    path = Path(cache) / f"{tile_name(lat, lon, product)}.tif"
    side = path.with_suffix(".json")
    meta = json.loads(side.read_text()) if side.exists() else {}
    if not (path.exists() and path.stat().st_size == signal["size"] and meta.get("etag") == signal["etag"]):
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(tile_url(lat, lon, product), tmp)
        if tmp.stat().st_size != signal["size"]:
            raise OSError(f"size mismatch for {path.name}")
        meta = {"etag": signal["etag"], "sha256": hashlib.sha256(tmp.read_bytes()).hexdigest()}
        tmp.replace(path)
        side.write_text(json.dumps(meta))
    return path, meta["sha256"]


def neighbours(lat: int, lon: int, have) -> list[tuple[int, int]]:
    """The tile and its 8 neighbours that exist in `have` (longitude wraps at the antimeridian)."""
    out: list[tuple[int, int]] = []
    for dla in (-1, 0, 1):
        la = lat + dla
        if la < -90 or la > 89:
            continue
        for dlo in (-1, 0, 1):
            lo = (lon + dlo + 180) % 360 - 180
            if (la, lo) in have and (la, lo) not in out:
                out.append((la, lo))
    return out
