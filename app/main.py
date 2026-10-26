from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.loki import send_log_to_loki, send_log_to_loki_async
from app.timezones import find_zone, format_offset, list_cities, parse_time

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Server Time API")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/time")
def get_time() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "utc": now.isoformat(),
        "local": now.astimezone().isoformat(),
        "timestamp": now.timestamp(),
    }


@app.get("/date")
def get_date() -> dict:
    now = datetime.now(timezone.utc)
    local = now.astimezone()
    return {
        "utc": now.date().isoformat(),
        "local": local.date().isoformat(),
        "weekday": local.strftime("%A"),
        "iso_week": local.isocalendar().week,
        "day_of_year": local.timetuple().tm_yday,
    }


@app.get("/datetime")
def get_datetime() -> dict:
    now = datetime.now(timezone.utc)
    local = now.astimezone()
    return {
        "date": local.date().isoformat(),
        "time": local.time().isoformat(),
        "timezone": local.tzname(),
        "iso": local.isoformat(),
    }


@app.get("/convert")
def convert_time(
    time: str = Query(..., description="Время UTC: 15.00, 15:00 или 15:00:30", examples=["15.00"]),
    tz: str = Query(..., description="Город, IANA-имя или аббревиатура", examples=["Екатеринбург"]),
) -> dict:
    parsed = parse_time(time)
    if parsed is None:
        send_log_to_loki_async(f"Некорректное время: time={time!r} tz={tz!r}", "warning", endpoint="convert")
        raise HTTPException(422, f"Не удалось разобрать время '{time}', ожидается формат 15.00 или 15:00")
    zone = find_zone(tz)
    if zone is None:
        send_log_to_loki_async(f"Неизвестный часовой пояс: time={time!r} tz={tz!r}", "warning", endpoint="convert")
        raise HTTPException(422, f"Неизвестный часовой пояс '{tz}'")

    utc_time, sep = parsed
    # Дата нужна, чтобы учесть летнее время: берём сегодняшнюю по UTC.
    source = datetime.combine(datetime.now(timezone.utc).date(), utc_time, timezone.utc)
    target = source.astimezone(zone)
    fmt = f"%H{sep}%M{sep}%S" if utc_time.second else f"%H{sep}%M"
    send_log_to_loki_async(
        f"Конвертация {source.strftime(fmt)} UTC -> {target.strftime(fmt)} {zone.key}", "info", endpoint="convert"
    )
    return {
        "utc": source.strftime(fmt),
        "time": target.strftime(fmt),
        "timezone": zone.key,
        "abbreviation": target.tzname(),
        "utc_offset": format_offset(target),
        "day_shift": (target.date() - source.date()).days,
    }


@app.get("/timezones")
def get_timezones() -> list[dict]:
    return list_cities()


class LogMessage(BaseModel):
    message: str = Field(..., min_length=1, examples=["Тестовое сообщение"])
    level: Literal["debug", "info", "warning", "error"] = "info"


@app.post("/log")
def post_log(entry: LogMessage) -> dict:
    """Отправляет произвольное сообщение в Loki — для проверки интеграции."""
    return {"sent": send_log_to_loki(entry.message, entry.level, endpoint="log")}
