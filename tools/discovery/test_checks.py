"""Source and resolution checks of the top zones (T43). Synthetic data only."""
import numpy as np
import pytest

from discovery.checks import compare_rankings


def test_rankings_report_rank_correlation_and_top_overlap_and_ignore_missing():
    nominal = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
    same = compare_rankings(nominal, nominal.copy(), top=2)
    assert same["spearman"] == pytest.approx(1.0) and same["top_overlap"] == 1.0 and same["zones"] == 5
    swapped = compare_rankings(nominal, np.array([0.5, 0.6, 0.7, 0.8, np.nan]), top=2)
    assert swapped["zones"] == 4 and swapped["spearman"] < 0 and swapped["top_overlap"] == 0.0
