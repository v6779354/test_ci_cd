from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Время сервера" in response.text


def test_health():
    response = client.get("/health")
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


def convert(time, tz):
    return client.get("/convert", params={"time": time, "tz": tz})


def test_convert_russian_city():
    response = convert("15.00", "Екатеринбург")
    assert response.status_code == 200
    data = response.json()
    assert data["time"] == "20.00"
    assert data["timezone"] == "Asia/Yekaterinburg"
    assert data["utc_offset"] == "+05:00"
    assert data["day_shift"] == 0


def test_convert_keeps_separator_and_seconds():
    assert convert("15:00", "Москва").json()["time"] == "18:00"
    assert convert("15:00:30", "москва").json()["time"] == "18:00:30"


def test_convert_other_name_forms():
    for tz in ("Asia/Yekaterinburg", "Yekaterinburg", "YEKT"):
        assert convert("15.00", tz).json()["time"] == "20.00"


def test_convert_crosses_midnight():
    data = convert("22.30", "Владивосток").json()
    assert data["time"] == "08.30"
    assert data["day_shift"] == 1


def test_convert_invalid_input():
    assert convert("25.00", "Москва").status_code == 422
    assert convert("пятнадцать", "Москва").status_code == 422
    assert convert("15.00", "Атлантида").status_code == 422
