import json
from datetime import datetime, timezone
from unittest import mock

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


def test_timezones_list():
    response = client.get("/timezones")
    assert response.status_code == 200
    cities = {c["name"]: c for c in response.json()}
    assert cities["Екатеринбург"] == {
        "name": "Екатеринбург", "zone": "Asia/Yekaterinburg", "utc_offset": "+05:00",
    }
    assert "Ростов-на-Дону" in cities
    assert "Санкт-Петербург" in cities
    assert "Спб" not in cities
    # Каждый город из списка должен находиться конвертером.
    for name in cities:
        assert convert("12.00", name).status_code == 200


class FakeResponse:
    status = 204

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_send_log_to_loki_posts_push_payload(monkeypatch):
    from app.loki import send_log_to_loki

    monkeypatch.setenv("LOKI_URL", "http://loki:3100/")
    with mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
        assert send_log_to_loki("привет", "error", endpoint="test") is True

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://loki:3100/loki/api/v1/push"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    stream = json.loads(request.data)["streams"][0]
    assert stream["stream"] == {"app": "server-time", "level": "error", "endpoint": "test"}
    timestamp, message = stream["values"][0]
    assert message == "привет"
    assert timestamp.isdigit() and len(timestamp) == 19


def test_send_log_to_loki_without_url_does_nothing(monkeypatch):
    from app.loki import send_log_to_loki

    monkeypatch.delenv("LOKI_URL", raising=False)
    with mock.patch("urllib.request.urlopen") as urlopen:
        assert send_log_to_loki("привет") is False
    urlopen.assert_not_called()


def test_send_log_to_loki_survives_loki_down(monkeypatch):
    from app.loki import send_log_to_loki

    monkeypatch.setenv("LOKI_URL", "http://loki:3100")
    with mock.patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        assert send_log_to_loki("привет") is False


def test_post_log_endpoint():
    with mock.patch("app.main.send_log_to_loki", return_value=True) as send:
        response = client.post("/log", json={"message": "проверка", "level": "warning"})
    assert response.status_code == 200
    assert response.json() == {"sent": True}
    send.assert_called_once_with("проверка", "warning", endpoint="log")
    assert client.post("/log", json={"message": "x", "level": "fatal"}).status_code == 422
