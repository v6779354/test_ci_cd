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


def test_date():
    response = client.get("/date")
    assert response.status_code == 200
    data = response.json()
    local = datetime.now().astimezone()
    assert data["utc"] == datetime.now(timezone.utc).date().isoformat()
    assert data["local"] == local.date().isoformat()
    assert data["weekday"] == local.strftime("%A")
    assert data["iso_week"] == local.isocalendar().week
    assert data["day_of_year"] == local.timetuple().tm_yday


def test_datetime():
    response = client.get("/datetime")
    assert response.status_code == 200
    data = response.json()
    iso = datetime.fromisoformat(data["iso"])
    assert iso.tzinfo is not None
    assert data["date"] == iso.date().isoformat()
    assert data["time"] == iso.time().isoformat()
    assert abs((datetime.now(timezone.utc) - iso).total_seconds()) < 5
