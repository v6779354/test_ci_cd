from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

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
