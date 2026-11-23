"""Tests of the data catalogue schema and renderer (data/catalog/*.yaml)."""
from pathlib import Path

import pytest

from catalog import STATUSES, load, render_markdown, validate

ROOT = Path(__file__).resolve().parents[2]


def entry(**over):
    e = {
        "id": "lro-lola-ldem-85s-40m", "body": "moon", "mission": "LRO", "instrument": "LOLA",
        "product": "LDEM_85S_40M", "producer": "NASA GSFC", "url": "https://example.org/lola",
        "access": {"format": "IMG", "size": "1 GB", "licence": "public domain", "account": False},
        "coverage": "85°S to 90°S", "resolution_spatial": "40 m", "resolution_effective": "coarser away from the pole",
        "resolution_temporal": "n/a", "units": "m", "nature": "derived", "uncertainty": "about 1 m vertical",
        "limitations": "interpolated between tracks", "dimensions": ["topography"], "environments": ["polar-highlands"],
        "status": "verified", "verified_on": "2026-11-18", "verified_url": "https://example.org/lola",
    }
    e.update(over)
    return e


def test_a_complete_entry_is_valid():
    assert validate([entry()]) == []


def test_missing_field_is_reported():
    e = entry()
    del e["coverage"]
    assert any("coverage" in err for err in validate([e]))


def test_nature_and_status_are_closed_lists():
    errs = validate([entry(nature="guess", status="probably")])
    assert any("nature" in err for err in errs) and any("status" in err for err in errs)


def test_verified_needs_date_and_source():
    errs = validate([entry(verified_on=None, verified_url=None)])
    assert any("verified_on" in err for err in errs)


def test_not_verified_entry_may_leave_facts_open():
    assert validate([entry(status="not verified", verified_on=None, verified_url=None, uncertainty="not verified")]) == []


def test_ids_are_unique():
    assert any("duplicate" in err for err in validate([entry(), entry()]))


def test_render_lists_every_entry_with_its_status():
    md = render_markdown([entry(), entry(id="x", product="Other", status="not available")], title="Moon")
    assert md.startswith("# Moon")
    assert "LDEM_85S_40M" in md and "Other" in md and "not available" in md


@pytest.mark.parametrize("path", sorted((ROOT / "data" / "catalog").glob("*.yaml")))
def test_repository_catalogues_are_valid(path):
    assert validate(load(path)) == []


def test_earth_entries_need_attribution_and_use():
    errs = validate([entry(body="earth")])
    assert any("attribution" in err for err in errs) and any("use" in err for err in errs)
    ok = entry(body="earth", attribution="Contains modified Copernicus data", use=["similarity", "mask"])
    assert validate([ok]) == []


def test_use_is_a_closed_list():
    bad = entry(body="earth", attribution="x", use=["decoration"])
    assert any("use" in err for err in validate([bad]))


def test_statuses():
    assert STATUSES == ("verified", "partly verified", "not verified", "not available")


# ---- T52: refresh block (ADR-009, section 1) ----

def refresh(**over):
    r = {"family": "pds", "signal": "ETag and Last-Modified of the files used", "interval": "weekly",
         "cadence": "Most LRO instrument teams release data every three months", "cadence_status": "verified",
         "checked_url": "https://example.org/lro", "checked_on": "2026-11-23"}
    r.update(over)
    return r


def test_a_refresh_block_is_valid():
    assert validate([entry(refresh=refresh())]) == []


def test_refresh_family_and_interval_are_closed_lists():
    errs = validate([entry(refresh=refresh(family="ftp", interval="hourly"))])
    assert any("family" in e for e in errs) and any("interval" in e for e in errs)


def test_a_verified_cadence_needs_its_page_and_date():
    errs = validate([entry(refresh=refresh(checked_url=None))])
    assert any("cadence" in e for e in errs)
    assert validate([entry(refresh=refresh(cadence="not stated on page", cadence_status="not verified",
                                           checked_url=None, checked_on=None))]) == []


def test_a_source_without_signal_is_not_checkable():
    """No machine signal: interval none, and the refresher reports `not_checkable`, never `up_to_date`."""
    assert validate([entry(refresh=refresh(family="none", signal=None, interval="none"))]) == []
    assert any("signal" in e for e in validate([entry(refresh=refresh(signal=None))]))


def test_every_source_of_a_release_has_a_refresh_block():
    """Every source a release names (Earth, planetary and context layers, both bodies) is watched (ADR-009)."""
    import json
    by_id = {e["id"]: e for p in (ROOT / "data" / "catalog").glob("*.yaml") for e in load(p)}
    used = {s["id"] for f in (ROOT / "data" / "releases-fixture").glob("r-*/method.json")
            for s in json.loads(f.read_text(encoding="utf-8"))["sources"]}
    assert len(used) >= 16
    assert sorted(i for i in used if "refresh" not in by_id.get(i, {})) == []


def test_watch_targets_need_the_keys_of_their_family():
    assert validate([entry(refresh=refresh(watch={"base": "https://p.example.org/", "files": {"a.img": 1}}))]) == []
    errs = validate([entry(refresh=refresh(family="s3", watch={"prefix": "x/"}))])
    assert any("watch" in e and "bucket" in e for e in errs)
    errs = validate([entry(refresh=refresh(family="page", watch={"url": "https://x.example.org"}))])
    assert any("pattern" in e for e in errs)


def test_new_products_need_a_page_and_a_pattern():
    assert validate([entry(refresh=refresh(new_products={"url": "https://p.example.org/", "pattern": "Release ([0-9]+)"}))]) == []
    assert any("new_products" in e for e in validate([entry(refresh=refresh(new_products={"url": "https://p.example.org/"}))]))
