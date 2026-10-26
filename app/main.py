from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="Server Time API")


@app.get("/")
def root() -> dict:
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
