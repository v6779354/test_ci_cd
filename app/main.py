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
