"""Unit tests for ingestion normalizer (pure functions)."""
from datetime import date

import pytest

from services.ingestion.normalizer import normalize_observation, parse_fred_observation


class TestParseFredObservation:
    def test_valid(self):
        d, v = parse_fred_observation({"date": "2024-01-15", "value": "3.4"})
        assert d == date(2024, 1, 15)
        assert v == 3.4

    def test_missing_value_dot(self):
        d, v = parse_fred_observation({"date": "2024-01-15", "value": "."})
        assert d == date(2024, 1, 15)
        assert v is None

    def test_missing_date(self):
        d, v = parse_fred_observation({"value": "3.4"})
        assert d is None
        assert v is None

    def test_invalid_date(self):
        d, v = parse_fred_observation({"date": "not-a-date", "value": "1"})
        assert d is None


class TestNormalizeObservation:
    def test_surprise_when_actual_and_forecast(self):
        out = normalize_observation(
            release_date=date(2024, 1, 15),
            actual=3.5,
            forecast=3.2,
            previous=3.0,
        )
        assert out["surprise"] == pytest.approx(0.3)
        assert out["actual"] == 3.5
        assert out["forecast"] == 3.2
        assert out["previous"] == 3.0
        assert out["surprise_normalized"] is None

    def test_no_surprise_when_forecast_missing(self):
        out = normalize_observation(
            release_date=date(2024, 1, 15),
            actual=3.5,
            previous=3.0,
        )
        assert out["surprise"] is None
        assert out["actual"] == 3.5

    def test_time_utc_midnight(self):
        out = normalize_observation(
            release_date=date(2024, 1, 15),
            actual=1.0,
        )
        assert out["time"].year == 2024
        assert out["time"].month == 1
        assert out["time"].day == 15
        assert out["time"].tzinfo is not None
