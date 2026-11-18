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


def test_statuses():
    assert STATUSES == ("verified", "partly verified", "not verified", "not available")
