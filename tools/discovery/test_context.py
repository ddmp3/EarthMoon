"""Earth context layers (T47, decision E18): frozen ground and aridity. Labelled; never a similarity with the Moon."""
import numpy as np
import pytest

from discovery.context import LAYERS, aridity_class, frozen_state, sample_stat


def test_frozen_ground_follows_threshold_e4_and_says_not_covered_outside_the_model():
    magt = np.array([-8.0, -6.0, -3.0, 0.5, np.nan])
    covered = np.array([True, True, True, True, False])
    assert frozen_state(magt, covered).tolist() == ["met", "met", "partial", "failed", "not covered"]


def test_aridity_uses_the_unep_classes():
    ai = np.array([0.01, 0.1, 0.3, 0.6, 0.9, np.nan])
    assert aridity_class(ai).tolist() == ["hyper-arid", "arid", "semi-arid", "dry sub-humid", "humid", "no data"]


def test_every_context_layer_says_its_class_and_what_it_does_not_mean():
    for name, meta in LAYERS.items():
        assert meta["class"] in ("direct", "indirect", "process", "model"), name
        assert meta["not_meaning"] and meta["source"], name
        assert "comparable_with_moon" in meta and meta["comparable_with_moon"] is False, name


def test_a_modelled_value_is_flagged_as_a_model():
    assert LAYERS["frozen_ground"]["class"] == "model"
    assert LAYERS["aridity"]["class"] == "model"


def test_multi_year_statistics_say_whether_they_carry_an_interannual_sigma():
    assert LAYERS["frozen_ground"]["interannual_sigma"] is False          # MAGT sd is the model spread, not interannual
    assert "not interannual" in LAYERS["frozen_ground"]["sigma"]
    assert LAYERS["aridity"]["interannual_sigma"] is False                 # 1970-2000 climatology


def test_no_elevation_correction_is_applied_to_any_temperature():
    # finding L9: an elevation correction on minimum temperatures fails in inversion-prone valleys
    for meta in LAYERS.values():
        assert meta.get("elevation_correction") is False


def test_cell_statistic_ignores_missing_samples_and_says_when_none_is_valid():
    v = np.array([[1.0, 2.0, np.nan], [np.nan, np.nan, np.nan]])
    med, n = sample_stat(v)
    assert med[0] == pytest.approx(1.5) and n.tolist() == [2, 0] and np.isnan(med[1])
