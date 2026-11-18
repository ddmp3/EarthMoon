"""Tests of the negative control draw (task T25)."""
from controls import NEGATIVE_CLASSES, draw_negatives, worldcover_tile


def test_tile_name_uses_the_3_degree_grid():
    assert worldcover_tile(45.5, 7.9) == "N45E006"
    assert worldcover_tile(-0.1, -0.1) == "S03W003"
    assert worldcover_tile(2.9, -179.5) == "N00W180"


def test_draw_takes_points_in_order_until_each_class_is_full():
    classes = iter([10, 10, 10, 10, 40, None, 50, 40, 40, 90, 80, 50, 50, 90, 90, 80, 80, 95, 95, 95])
    pts = [(i, i) for i in range(20)]
    out = draw_negatives(pts, lambda lat, lon: next(classes), per_class=3)
    by = {}
    for o in out:
        by.setdefault(o["class"], []).append(o["lat"])
    assert by[10] == [0, 1, 2] and by[40] == [4, 7, 8] and by[50] == [6, 11, 12]
    assert len(out) == 18 and set(by) == set(NEGATIVE_CLASSES)


def test_ocean_and_other_classes_are_skipped():
    out = draw_negatives([(0, 0), (1, 1)], lambda lat, lon: None if lat == 0 else 60, per_class=1)
    assert out == []


def test_repository_positive_controls_follow_the_rule():
    import json
    import re
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[2]
    data = yaml.safe_load((root / "data" / "validation" / "positives.yaml").read_text(encoding="utf-8"))
    refs = (root / "docs" / "REFERENCES.md").read_text(encoding="utf-8")
    for name, sc in data["scenarios"].items():
        for c in sc.get("controls", []):
            assert -90 <= c["lat"] <= 90 and -180 <= c["lon"] <= 180 and c["gazetteer"]
        if sc.get("controls"):
            row = re.search(rf"^\| {sc['reference']} \|.*\| verified \|", refs, re.M)
            assert row, f"{name}: {sc['reference']} must be a verified reference"
            assert sc["quote"] and sc["function"]
