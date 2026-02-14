"""Unit tests for processing surprise normalization (pure function)."""
import pytest

from services.processing.surprise import normalize_surprise


class TestNormalizeSurprise:
    def test_zero_when_mean_none(self):
        assert normalize_surprise(1.0, None, 0.5) == 0.0

    def test_normalized_and_capped(self):
        # (x - mean) / std = (5 - 2) / 2 = 1.5
        assert normalize_surprise(5.0, 2.0, 2.0, cap=3.0) == pytest.approx(1.5)
        # cap 1.0 -> 1.0
        assert normalize_surprise(5.0, 2.0, 2.0, cap=1.0) == pytest.approx(1.0)
        assert normalize_surprise(0.0, 2.0, 2.0, cap=1.0) == pytest.approx(-1.0)

    def test_std_zero_uses_eps(self):
        # scale = max(eps, 0) = eps, so (x - mean) / eps is large -> capped
        out = normalize_surprise(1.0, 1.0, 0.0, cap=3.0, eps=1e-8)
        assert out == 0.0  # (1-1)/eps = 0

    def test_negative_cap(self):
        assert normalize_surprise(-2.0, 0.0, 1.0, cap=2.0) == pytest.approx(-2.0)
        assert normalize_surprise(-5.0, 0.0, 1.0, cap=2.0) == pytest.approx(-2.0)
