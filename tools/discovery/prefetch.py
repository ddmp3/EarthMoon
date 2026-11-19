"""Download Copernicus tiles into the local cache with many parallel connections (T43).

The fine stage streams GLO-30 once per pixel scale; downloading each tile once and reading it from disk for both
scales halves the network work, and parallel connections use the available bandwidth. Files are written by
`copernicus.local_copy` (ETag check, sidecar with SHA-256), exactly as `cube.py --cache` does, so the run that
follows finds them and downloads nothing.

    PYTHONPATH=tools python tools/discovery/prefetch.py --listing L.json --tiles a.txt b.txt --cache /data/copernicus-glo30
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from discovery.copernicus import local_copy, neighbours  # noqa: E402


def needed(tiles: list[tuple[int, int]], have: set) -> list[tuple[int, int]]:
    """Each tile and its existing neighbours (the fine stage reads neighbours for complete edges)."""
    return sorted({n for t in tiles for n in neighbours(*t, have)})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing", type=Path, required=True)
    ap.add_argument("--tiles", type=Path, nargs="+", required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--product", default="glo30")
    ap.add_argument("--threads", type=int, default=48)
    ap.add_argument("--limit", type=int, default=0, help="first N tiles only (throughput test)")
    a = ap.parse_args(argv)
    listing = {tuple(map(int, k.split(","))): v for k, v in json.loads(a.listing.read_text()).items()}
    tiles = sorted({tuple(int(v) for v in x.split(",")) for f in a.tiles for x in f.read_text().split()} & set(listing))
    todo = needed(tiles, set(listing))
    if a.limit:
        todo = todo[:a.limit]
    a.cache.mkdir(parents=True, exist_ok=True)
    total = sum(listing[t]["size"] for t in todo)
    print(f"{len(todo)} files, {total / 1e9:.1f} GB, {a.threads} connections", flush=True)
    t0, done, nbytes, failed = time.time(), 0, 0, []
    with ThreadPoolExecutor(max_workers=a.threads) as pool:
        futs = {pool.submit(local_copy, *t, a.product, a.cache, listing[t]): t for t in todo}
        for f in as_completed(futs):
            t = futs[f]
            try:
                f.result()
                done += 1
                nbytes += listing[t]["size"]
            except OSError as e:
                failed.append({"tile": t, "error": f"{type(e).__name__}: {e}"})
            if done % 500 == 0 and done:
                dt = time.time() - t0
                print(f"{done}/{len(todo)} files, {nbytes / 1e9:.1f} GB, {nbytes / dt / 1e6:.0f} MB/s, {dt / 3600:.2f} h", flush=True)
    dt = time.time() - t0
    print(f"done {done}, failed {len(failed)}, {nbytes / 1e9:.1f} GB in {dt / 3600:.2f} h ({nbytes / max(dt, 1e-9) / 1e6:.0f} MB/s)", flush=True)
    (a.cache / "prefetch-failed.json").write_text(json.dumps(failed, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
