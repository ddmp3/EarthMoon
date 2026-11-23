"""End-to-end functional tests against the running application.

    docker compose up --build -d
    python tools/validation/e2e.py                       # front http://localhost:8080, API http://localhost:3001
    python tools/validation/e2e.py --web URL --api URL   # another environment (Azure)

Each test has an identifier (TF-xx). Exit code 0 if everything passes. Standard library only.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

RESULTS: list[tuple[str, bool, str]] = []


def http(url: str, method: str = "GET", body=None, headers=None, timeout: int = 120):
    data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, dict(res.headers), res.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def check(test_id: str, label: str, fn) -> None:
    try:
        detail = fn() or ""
        RESULTS.append((test_id, True, f"{label}{' : ' + detail if detail else ''}"))
    except AssertionError as e:
        RESULTS.append((test_id, False, f"{label} : {e}"))
    except Exception as e:  # network error, unreadable JSON
        RESULTS.append((test_id, False, f"{label} : {type(e).__name__}: {e}"))


def run(web: str, api: str) -> None:
    origin = web.rstrip("/")

    def front_loads():
        code, _, html = http(f"{web}/")
        assert code == 200, f"HTTP {code}"
        page = html.decode("utf-8", "replace")
        assert "<div id=\"root\"" in page, "React mount point missing"
        scripts = re.findall(r'src="(/assets/[^"]+\.js)"', page)
        assert scripts, "no JS bundle"
        code, _, js = http(f"{web}{scripts[0]}")
        assert code == 200 and len(js) > 10_000, "unreadable JS bundle"
        assert api.rstrip("/").encode() in js, f"the bundle does not call {api}"
        return f"bundle {len(js) // 1024} KB, API {api}"

    def health():
        code, _, b = http(f"{api}/api/health")
        assert code == 200 and json.loads(b) == {"status": "ok"}, f"HTTP {code}"

    def cors():
        code, h, _ = http(f"{api}/api/analyze", "OPTIONS", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        allowed = {k.lower(): v for k, v in h.items()}.get("access-control-allow-origin")
        assert allowed == origin, f"origin {origin} rejected ({allowed})"
        _, h2, _ = http(f"{api}/api/modes", headers={"Origin": "https://unknown.example"})
        assert "access-control-allow-origin" not in {k.lower() for k in h2}, "unknown origin accepted"

    analyses: dict[str, list[dict]] = {}

    def mode(m):
        def fn():
            code, _, b = http(f"{api}/api/analyze", "POST", {"mode": m})
            assert code == 200, f"HTTP {code}"
            sites = json.loads(b)["sites"]
            assert len(sites) >= 30, f"{len(sites)} sites"
            body = json.loads(b)
            assert body["methodology"]["version"] and body["methodology"].get("dataset"), "methodology or data set version missing"
            ranked = [s for s in sites if not s.get("excluded")]
            totals = [s["total"] for s in ranked]
            # Sites failing a hard requirement come after the others; each group is sorted by descending total.
            passing = [s["total"] for s in ranked if s["requirements"] != "failed"]
            failing = [s["total"] for s in ranked if s["requirements"] == "failed"]
            assert totals == passing + failing, "a site failing a requirement ranks above a passing site"
            assert passing == sorted(passing, reverse=True) and failing == sorted(failing, reverse=True), "ranking not sorted"
            assert all(0 <= t <= 100 for t in totals), "score outside 0-100"
            for s in ranked:
                assert 0 <= s["coverage"] <= 1 and s["totalRange"]["min"] <= s["total"] <= s["totalRange"]["max"], f"{s['id']}: inconsistent coverage or bounds"
                assert (s["coverage"] < 1) == bool(s.get("missing")), f"{s['id']}: coverage and missing criteria disagree"
                assert s["confidence"] in ("high", "medium", "low"), f"{s['id']}: no confidence label"
            excluded = [s for s in sites if s.get("excluded")]
            assert sites[-len(excluded):] == excluded if excluded else True, "excluded sites are not last"
            amazon = next(s for s in sites if s["role"] == "negative")
            assert amazon.get("excluded") == "vegetation", "negative control not excluded"
            missing = sum(c["verdict"] == "missing" for s in sites for c in s["criteria"])
            analyses[m] = sites
            return f"{len(sites)} sites, first {sites[0]['id']} ({sites[0]['total']}), {missing} criteria without a value"
        return fn

    def stability():
        sites = analyses.get("robotics")
        assert sites, "robotics analysis missing (TF-04 failed?)"
        code, _, b = http(f"{api}/api/analyze", "POST", {"mode": "robotics"})
        body = json.loads(b)
        meta = body["sensitivity"]
        assert meta["runs"] >= 100 and "weights" in meta["perturbation"], "sensitivity method not described"
        ranked = [s for s in body["sites"] if not s.get("excluded")]
        for s in ranked:
            st = s["stability"]
            assert 1 <= st["rankP10"] <= st["rankMedian"] <= st["rankP90"] <= len(ranked), f"{s['id']}: inconsistent rank range"
            assert 0 <= st["topHalfShare"] <= 1, f"{s['id']}: topHalfShare outside 0-1"
        assert not any("stability" in s for s in body["sites"] if s.get("excluded")), "excluded site has a rank range"
        again = json.loads(http(f"{api}/api/analyze", "POST", {"mode": "robotics"})[2])
        assert [s.get("stability") for s in again["sites"]] == [s.get("stability") for s in body["sites"]], "not deterministic"
        stable = sum(1 for s in ranked if s["stability"]["rankP90"] - s["stability"]["rankP10"] <= 2)
        return f"{len(ranked)} ranked sites, {stable} with a rank range of 2 places or less"

    def vegetation():
        code, _, b = http(f"{api}/api/analyze", "POST", {"mode": "colony"})
        sites = json.loads(b)["sites"]
        penalized = [s for s in sites if "vegetationFactor" in s]
        assert penalized, "no site penalized by vegetation (graded filter missing?)"
        assert all(0 < s["vegetationFactor"] < 1 and not s.get("excluded") for s in penalized), "inconsistent factor"
        off = json.loads(http(f"{api}/api/analyze", "POST", {"mode": "colony", "bareSoilOnly": False})[2])["sites"]
        raw = {s["id"]: s["total"] for s in off}
        assert all(s["total"] <= raw[s["id"]] for s in penalized), "penalty raised a score"
        return ", ".join(f"{s['id']} ×{s['vegetationFactor']}" for s in penalized)

    def custom():
        crit = [{"param": "t2m_mean", "max": -10, "tolerance": 10, "weight": 2}, {"param": "wind", "max": 3, "tolerance": 3, "weight": 1}]
        code, _, b = http(f"{api}/api/analyze", "POST", {"criteria": crit, "bareSoilOnly": False})
        assert code == 200, f"HTTP {code}"
        sites = json.loads(b)["sites"]
        assert not any(s.get("excluded") for s in sites), "bare-soil filter active although it is disabled"
        assert all(len(s["criteria"]) == 2 for s in sites)
        return f"first {sites[0]['id']} ({sites[0]['total']})"

    def custom_invalid():
        for body, why in [({"criteria": []}, "empty list"),
                          ({"criteria": [{"param": "gravity", "max": 1, "tolerance": 1, "weight": 1}]}, "unknown parameter"),
                          ({"mode": "mars"}, "unknown mode"),
                          (b"{not json", "unreadable JSON")]:
            code, _, b = http(f"{api}/api/analyze", "POST", body)
            assert code == 400, f"{why} : HTTP {code}"
            assert "error" in json.loads(b), f"{why} : no error message"

    def detail():
        code, _, b = http(f"{api}/api/sites/haughton?mode=robotics")
        assert code == 200, f"HTTP {code}"
        d = json.loads(b)
        for key in ("values", "valueSources", "moon", "criteria", "sources"):
            assert key in d, f"champ {key} absent"
        known = [k for k, v in d["values"].items() if isinstance(v, (int, float))]
        assert set(known) <= set(d["valueSources"]), "value without a source"
        assert "fixtures" not in d["valueSources"].values(), "sample data served in real mode"
        assert "slope_mean" in d["moon"] and "source" in d["moon"]["slope_mean"], "lunar reference missing"
        code, _, _ = http(f"{api}/api/sites/inconnu")
        assert code == 404, f"site inconnu : HTTP {code}"
        return f"{len(known)} sourced values, {len(d['moon'])} lunar references"

    def sources():
        code, _, b = http(f"{api}/api/sources")
        assert code == 200
        s = json.loads(b)["sources"]
        assert all(x["name"] and x["url"].startswith("https://") and x["terms"] for x in s), "incomplete source"
        return ", ".join(x["id"] for x in s)

    def moon_reference():
        code, _, b = http(f"{api}/api/reference/moon")
        assert code == 200
        ref = json.loads(b)
        limits = {x["id"] for x in ref.get("earth_limits", [])}
        assert {"gravity", "vacuum", "radiation"} <= limits, f"limits missing: {limits}"
        assert all("source" in p for p in ref["params"].values()), "lunar parameter without a source"

    def docs():
        code, _, b = http(f"{api}/api/docs/")
        assert code == 200 and b"swagger" in b.lower()

    def visuals():
        code, _, b = http(f"{web}/sites/manifest.json")
        assert code == 200, f"manifest HTTP {code}"
        m = json.loads(b)
        assert len(m["sites"]) >= 30 and len(m["slope_band_deg"]) == 2, "incomplete manifest"
        sid = next(iter(m["sites"]))
        for path in (f"/sites/{sid}/earth-relief.jpg", f"/sites/{sid}/moon-relief.jpg", f"/sites/{sid}/moon-match.png",
                     "/img/hero.jpg", "/img/robotics.jpg", "/img/calibration.jpg", "/img/colony.jpg", "/img/custom.jpg"):
            code, h, body = http(f"{web}{path}")
            kind = {k.lower(): v for k, v in h.items()}.get("content-type", "")
            assert code == 200 and kind.startswith("image/") and len(body) > 5000, f"{path} : HTTP {code} {kind}"
        twins = [v["twin"] for v in m["sites"].values()]
        assert all(t["lat"] <= -85 for t in twins), "lunar twin outside the south pole"
        return f"{len(m['sites'])} illustrated sites, {sum(1 for v in m['sites'].values() if v.get('photo'))} satellite views"

    def v3_static():
        code, _, b = http(f"{api}/api/v3/releases")
        assert code == 200, f"releases HTTP {code}"
        idx = json.loads(b)
        code, _, b = http(f"{api}/api/v3/scenarios")
        sc = json.loads(b)["scenarios"]
        s = next(x for x in sc if x["assessed_targets"])
        env = s["assessed_targets"][0]
        code, _, b = http(f"{api}/api/v3/zones?scenario={s['id']}&env={env}&limit=5")
        assert code == 200, f"zones HTTP {code}"
        z = json.loads(b)
        assert z["release"] == idx["current"] and z["methodology_version"], "release missing"
        if z["zones"]:
            code, _, b = http(f"{api}/api/v3/zones/{z['zones'][0]['id']}")
            card = json.loads(b)["zone"]
            assert code == 200 and set(card["typicality"]) == {"median", "p25", "p75"}, "zone card without spread"
        code, _, b = http(f"{api}/api/v3/coverage?scenario={s['id']}&env={env}")
        assert code == 200 and "screened_out" in json.loads(b)["coverage"]["classes"], "coverage classes missing"
        code, _, b = http(f"{api}/api/v3/method")
        assert code == 200 and json.loads(b)["sources"], "no source in the method panel"
        code, _, b = http(f"{api}/api/v3/status")
        st = json.loads(b)
        assert code == 200 and st["validity"]["state"] in ("validated", "not_validated") and st["freshness"]["sources"], "status incomplete"
        assert http(f"{api}/api/v3/zones?scenario={s['id']}&env={env}&tau=0.66")[0] == 400, "tau outside the grid accepted"
        return f"release {idx['current']} ({idx['releases'][0]['run']}), {z['total']} zones for {s['id']} {env}"

    def v3_layers_and_service():
        sc = json.loads(http(f"{api}/api/v3/scenarios")[2])["scenarios"]
        s = next(x for x in sc if x["assessed_targets"])
        env = s["assessed_targets"][0]
        z = json.loads(http(f"{api}/api/v3/zones?scenario={s['id']}&env={env}&limit=1")[2])["zones"]
        assert z, "no zone to look at"
        lat, lon = z[0]["lat"], z[0]["lon"]
        import math
        n = 2 ** 7                                                    # the zoom-7 tile that holds the first zone
        tx = int((lon + 180) / 360 * n)
        ty = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
        code, h, b = http(f"{api}/api/v3/layers/{s['id']}/{env}/typicality/7/{tx}/{ty}.png")
        kind = {k.lower(): v for k, v in h.items()}.get("content-type", "")
        assert code == 200 and kind == "image/png" and b[:8] == bytes.fromhex("89504e470d0a1a0a"), f"tile HTTP {code} {kind}"
        assert http(f"{api}/api/v3/layers/{s['id']}/{env}/coverage/9/0/0.png")[0] == 400, "zoom 9 accepted"
        bbox = f"{lon - 0.2},{lat - 0.2},{lon + 0.2},{lat + 0.2}"
        code, _, b = http(f"{api}/api/v3/cells?scenario={s['id']}&env={env}&bbox={bbox}")
        assert code == 200, f"cells HTTP {code}: {b[:200]!r}"
        fc = json.loads(b)
        code, _, b = http(f"{api}/api/v3/query", "POST", {"scenario": s["id"], "env": env, "min_typicality": 0.5, "limit": 5})
        assert code == 200, f"query HTTP {code}: {b[:200]!r}"
        q = json.loads(b)
        assert http(f"{api}/api/v3/query", "POST", {"scenario": s["id"], "env": env, "colour": "red"})[0] == 400, "unknown field accepted"
        return f"{len(fc['features'])} cells in view, query matched {q['matched']}"

    def v3_mars():
        idx = json.loads(http(f"{api}/api/v3/releases")[2])
        mars = (idx.get("current_by_body") or {}).get("mars")
        assert mars, "no Mars release in the index"
        code, _, b = http(f"{api}/api/v3/scenarios?release=mars")
        assert code == 200, f"scenarios HTTP {code}"
        doc = json.loads(b)
        assert doc["release"] == mars and [s["id"] for s in doc["scenarios"]] == ["D"], "release=mars does not read scenario D"
        d = doc["scenarios"][0]
        assert all(t.startswith("mars-") for t in d["assessed_targets"]), "a lunar target in scenario D"
        env = d["assessed_targets"][0]
        z = json.loads(http(f"{api}/api/v3/zones?scenario=D&env={env}&limit=1&release=mars")[2])["zones"]
        assert z, "no Mars zone"
        lat, lon = z[0]["lat"], z[0]["lon"]
        code, _, b = http(f"{api}/api/v3/cells?scenario=D&env={env}&bbox={lon - 0.2},{lat - 0.2},{lon + 0.2},{lat + 0.2}&release=mars")
        assert code == 200, f"Mars cells HTTP {code}: {b[:200]!r}"
        st = json.loads(http(f"{api}/api/v3/status?release=mars")[2])
        assert st["validity"]["protocol"] == "validation-protocol-mars-v1", "Mars status not under protocol mars-v1"
        assert json.loads(http(f"{api}/api/v3/scenarios")[2])["release"] == idx["current"], "the default release is not the lunar one"
        return f"release {mars}, {len(d['assessed_targets'])} targets, {len(json.loads(b)['features'])} cells in view"

    check("TF-01", "Front end loads and targets the right API", front_loads)
    check("TF-02", "API health probe", health)
    check("TF-03", "CORS: front-end origin accepted, unknown origin rejected", cors)
    check("TF-04", "Mode 1, robotics validation", mode("robotics"))
    check("TF-05", "Mode 2, instrument calibration", mode("calibration"))
    check("TF-06", "Mode 3, self-sufficient colony", mode("colony"))
    check("TF-07", "Mode 4, free criteria, bare-soil filter off", custom)
    check("TF-08", "Invalid requests rejected with a message (400)", custom_invalid)
    check("TF-09", "Site card: values, source of each value, lunar reference; 404 unknown site", detail)
    check("TF-10", "Complete source catalog", sources)
    check("TF-11", "Sourced lunar profile and Earth limits", moon_reference)
    check("TF-12", "API documentation", docs)
    check("TF-13", "Real images: NASA photos, site views, lunar twins", visuals)
    check("TF-14", "Rank stability: ranges consistent, deterministic, none for excluded sites", stability)
    check("TF-15", "Graded vegetation filter: penalized sites kept, never boosted", vegetation)
    check("TF-16", "v3: releases, zones, zone card with spread, coverage, method; grid enforced", v3_static)
    check("TF-17", "v3: layer tiles, cells in view and custom query through the internal service", v3_layers_and_service)
    check("TF-18", "v3 Mars (T48): release=mars reads scenario D, its zones and cells; the default stays lunar", v3_mars)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--web", default="http://localhost:8080")
    ap.add_argument("--api", default="http://localhost:3001")
    args = ap.parse_args(argv)
    run(args.web.rstrip("/"), args.api.rstrip("/"))
    for test_id, ok, text in RESULTS:
        print(f"{'OK  ' if ok else 'FAIL '} {test_id}  {text}")
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} tests passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
