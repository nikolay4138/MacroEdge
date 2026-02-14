"""API tests with FastAPI TestClient. Endpoints that need DB are mocked to return empty data."""
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in os.environ.get("PYTHONPATH", ""):
    os.environ["PYTHONPATH"] = str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")


@pytest.fixture
def client_no_db():
    """TestClient with DB mocked so fetch_all returns [] (no real DB needed)."""
    async def mock_fetch_all(*args, **kwargs):
        return []

    with patch("services.core.db.fetch_all", new_callable=AsyncMock, side_effect=mock_fetch_all):
        with TestClient(app) as c:
            yield c


# Import after path setup
from services.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_returns_ok_or_error():
    r = client.get("/ready")
    assert r.status_code == 200
    j = r.json()
    assert "status" in j
    assert j["status"] in ("ok", "error")
    if j["status"] == "ok":
        assert j.get("database") == "connected"


def test_indices():
    r = client.get("/api/v1/indices")
    assert r.status_code == 200
    j = r.json()
    assert "indices" in j
    indices = j["indices"]
    assert isinstance(indices, list)
    if indices:
        assert "code" in indices[0]
        assert "name" in indices[0]
        codes = [x["code"] for x in indices]
        assert "SPX" in codes or len(codes) >= 1


def test_bias_summary_structure(client_no_db):
    r = client_no_db.get("/api/v1/bias/summary")
    assert r.status_code == 200
    j = r.json()
    assert "scores" in j
    assert isinstance(j["scores"], list)
    assert "date" in j
    # When no rows from DB, we get empty scores and a message
    if not j["scores"]:
        assert "message" in j or j["date"] is None


def test_bias_history_structure(client_no_db):
    r = client_no_db.get("/api/v1/bias/history?limit=5")
    assert r.status_code == 200
    j = r.json()
    assert "series" in j
    assert "count" in j
    assert isinstance(j["series"], list)
    assert j["count"] == 0


def test_macro_latest_structure(client_no_db):
    r = client_no_db.get("/api/v1/macro/latest?days=7")
    assert r.status_code == 200
    j = r.json()
    assert "observations" in j
    assert "count" in j
    assert isinstance(j["observations"], list)
    assert j["count"] == 0
