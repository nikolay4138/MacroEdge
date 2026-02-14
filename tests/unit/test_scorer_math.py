"""Unit tests for bias scorer pure functions."""
import pytest

from services.bias_engine.scorer import (
    risk_flag_from_thresholds,
    score_bounded,
    score_raw,
    signed_surprise,
)


class TestSignedSurprise:
    def test_positive_direction(self):
        assert signed_surprise("positive", 1.5) == 1.5
        assert signed_surprise("positive", -1.0) == -1.0

    def test_negative_direction(self):
        assert signed_surprise("negative", 1.5) == -1.5
        assert signed_surprise("negative", -1.0) == 1.0


class TestScoreRaw:
    def test_sum_weighted(self):
        # (0.5 * 1) + (0.5 * -1) = 0
        assert score_raw([(0.5, 1.0), (0.5, -1.0)]) == pytest.approx(0.0)
        assert score_raw([(1.0, 2.0)]) == pytest.approx(2.0)

    def test_empty(self):
        assert score_raw([]) == 0.0


class TestScoreBounded:
    def test_tanh_bounds(self):
        assert -100 <= score_bounded(0.0, 2.0) <= 100
        assert score_bounded(0.0, 2.0) == pytest.approx(0.0)
        # large raw -> approaches 100
        assert score_bounded(100.0, 2.0) == pytest.approx(100.0, abs=1.0)
        assert score_bounded(-100.0, 2.0) == pytest.approx(-100.0, abs=1.0)

    def test_lambda_scale(self):
        # smaller lambda -> more sensitivity
        s1 = score_bounded(1.0, 1.0)
        s2 = score_bounded(1.0, 4.0)
        assert abs(s1) > abs(s2)


class TestRiskFlagFromThresholds:
    """Uses get_settings().get_bias_engine_config() - needs config dir."""

    def test_high_vix_critical(self):
        # vix >= 45 -> high
        assert risk_flag_from_thresholds(80, 30, 50.0, "neutral") == "high"

    def test_low_confidence_high(self):
        # confidence <= 40 -> high
        assert risk_flag_from_thresholds(30, 20, None, "neutral") == "high"

    def test_low_risk(self):
        # confidence >= 70, |bias| <= 50, vix low -> low
        assert risk_flag_from_thresholds(75, 30, 15.0, "neutral") == "low"
        assert risk_flag_from_thresholds(75, 30, None, "neutral") == "low"

    def test_medium_else(self):
        assert risk_flag_from_thresholds(50, 60, None, "neutral") == "medium"
