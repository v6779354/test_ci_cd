from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_time():
    response = client.get("/time")
    assert response.status_code == 200
    data = response.json()
    utc = datetime.fromisoformat(data["utc"])
    assert utc.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - utc).total_seconds()) < 5
    assert "local" in data
    assert isinstance(data["timestamp"], float)
