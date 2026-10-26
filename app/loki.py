import json
import logging
import os
import threading
import time
import urllib.request

logger = logging.getLogger(__name__)

APP_LABEL = "server-time"


def loki_url() -> str | None:
    """Адрес Loki из переменной окружения LOKI_URL, например http://loki:3100."""
    url = os.getenv("LOKI_URL", "").strip()
    return url.rstrip("/") or None


def build_payload(message: str, level: str, labels: dict[str, str]) -> dict:
    stream = {"app": APP_LABEL, "level": level, **labels}
    # Loki ждёт время в наносекундах строкой.
    return {"streams": [{"stream": stream, "values": [[str(time.time_ns()), message]]}]}


def send_log_to_loki(message: str, level: str = "info", **labels: str) -> bool:
    """Отправляет одно сообщение в Loki через POST /loki/api/v1/push.

    Возвращает True, если Loki принял сообщение. Ошибки не пробрасываются:
    падение Loki не должно ломать само приложение.
    """
    url = loki_url()
    if url is None:
        return False
    body = json.dumps(build_payload(message, level, labels)).encode()
    request = urllib.request.Request(
        f"{url}/loki/api/v1/push",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 204
    except OSError as exc:
        logger.warning("Не удалось отправить лог в Loki: %s", exc)
        return False


def send_log_to_loki_async(message: str, level: str = "info", **labels: str) -> None:
    """То же, но в фоновом потоке, чтобы не задерживать ответ на запрос."""
    threading.Thread(
        target=send_log_to_loki, args=(message, level), kwargs=labels, daemon=True
    ).start()
