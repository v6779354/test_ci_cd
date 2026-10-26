# Server Time API

Учебный бэкенд на FastAPI: показывает текущее время сервера и переводит время из UTC в другие часовые пояса. На примере проекта настроен CI/CD: GitHub Actions собирает Docker-образ, публикует его в GitHub Container Registry и разворачивает на сервере по SSH.

## Возможности

- Веб-страница на `/`: часы сервера, дата, часовой пояс, номер недели, прогресс года и конвертер времени из UTC с подсказками городов.
- JSON API с текущим временем, датой и конвертацией между часовыми поясами.
- Автоматическая сборка и деплой при каждом push в `main`.
- Сбор логов в Loki и их просмотр в Grafana; приложение само отправляет события в Loki.

## API

| Метод и путь | Что возвращает |
|---|---|
| `GET /` | Веб-страница |
| `GET /health` | `{"status": "ok"}` — проверка, что сервер жив |
| `GET /time` | Время в UTC, в поясе сервера и Unix timestamp |
| `GET /date` | Дата в UTC и в поясе сервера, день недели, неделя ISO, день года |
| `GET /datetime` | Дата, время и часовой пояс сервера |
| `GET /convert?time=…&tz=…` | Время UTC, переведённое в указанный пояс |
| `GET /timezones` | Список городов для подсказок с их смещением от UTC |
| `POST /log` | Отправляет сообщение в Loki: `{"message": "…", "level": "info"}` → `{"sent": true}` |
| `GET /docs` | Интерактивная документация (Swagger UI) |

### Конвертация времени

```
GET /convert?time=15.00&tz=Екатеринбург
```

```json
{
  "utc": "15.00",
  "time": "20.00",
  "timezone": "Asia/Yekaterinburg",
  "abbreviation": "+05",
  "utc_offset": "+05:00",
  "day_shift": 0
}
```

- `time` — время UTC в формате `15.00`, `15:00` или `15:00:30`. Ответ приходит с тем же разделителем.
- `tz` — часовой пояс, регистр не важен. Можно указать:
  - город по-русски (около 80 городов России, СНГ и мира): `Москва`, `Екатеринбург`, `Нью-Йорк`;
  - город по-английски, из базы IANA: `Yekaterinburg`, `New York`;
  - IANA-имя: `Asia/Yekaterinburg`;
  - аббревиатуру: `MSK`, `YEKT`, `UTC`, `PST`.
- `day_shift` — сдвиг дня: `1`, если в целевом поясе уже следующие сутки, `-1` — если ещё предыдущие.
- Летнее время учитывается на сегодняшнюю дату по UTC.
- Нераспознанное время или пояс → ответ `422` с текстом ошибки.

## Структура проекта

```
app/
  main.py          эндпоинты FastAPI
  timezones.py     поиск часового пояса по названию, разбор времени, список городов
  loki.py          send_log_to_loki — отправка логов в Loki
  static/
    index.html     веб-страница (HTML, CSS и JS в одном файле, без зависимостей)
tests/
  test_main.py     тесты API
Dockerfile
.github/workflows/deploy.yml   CI/CD
requirements.txt       зависимости приложения
requirements-dev.txt   зависимости для тестов
```

## Локальный запуск

Нужен Python 3.12.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
```

Страница откроется на http://127.0.0.1:8000, документация API — на http://127.0.0.1:8000/docs.

Тесты:

```bash
.venv/bin/pytest -q
```

## Docker

```bash
docker build -t server-time .
docker run --rm -p 8000:8000 server-time
```

Образ основан на `python:3.12-slim`, приложение запускается от непривилегированного пользователя `appuser`. В образ попадают только `app/` и зависимости из `requirements.txt`, тесты исключены через `.dockerignore`.

База часовых поясов ставится пакетом `tzdata` из `requirements.txt`, потому что в `slim`-образе её может не быть.

Часовой пояс контейнера по умолчанию UTC. Другой можно задать переменной окружения: `-e TZ=Europe/Moscow`.

## CI/CD

Workflow [.github/workflows/deploy.yml](.github/workflows/deploy.yml) запускается при push в `main` и вручную (Actions → Build and deploy → Run workflow).

1. **Build and push image** — собирает образ и публикует в `ghcr.io/<владелец>/<репозиторий>` с тегами `latest` и `sha-<коммит>`. Для входа в реестр используется встроенный `GITHUB_TOKEN`.
2. **Deploy to server** — по SSH заходит на сервер, скачивает образ с тегом текущего коммита и перезапускает контейнер `server-time` на порту 8000 (`--restart unless-stopped`). Контейнер подключается к сети `logging` стека логирования и получает `LOKI_URL=http://loki:3100`; если сети нет, деплой её создаёт.

Сервер всегда получает образ конкретного коммита, поэтому видно, какая версия запущена: `docker ps` показывает тег `sha-…`.

### Секреты репозитория

Settings → Secrets and variables → Actions → Repository secrets:

| Секрет | Значение |
|---|---|
| `SSH_HOST` | IP-адрес или домен сервера |
| `SSH_USER` | пользователь для деплоя (`deploy`) |
| `SSH_PRIVATE_KEY` | приватный SSH-ключ этого пользователя целиком |
| `SSH_PORT` | необязательный, по умолчанию `22` |

Если секретов нет, джоба деплоя падает с ошибкой `missing server host`.

## Логирование: Loki + Grafana

Стек развёрнут на сервере отдельным Docker Compose-проектом в `/opt/Loki+Grafana/docker-compose.yml`. В репозитории его нет: в файле задан пароль администратора Grafana.

| Сервис | Образ | Роль | Доступ |
|---|---|---|---|
| `loki` | `grafana/loki:3.5.0` | Хранит логи, срок хранения 7 дней | `127.0.0.1:3100`, только с сервера и из сети `logging` |
| `grafana` | `grafana/grafana:12.0.0` | Просмотр логов и дашборды; источник Loki подключается автоматически | порт 3000, пользователь `admin` |
| `alloy` | `grafana/alloy:v1.12.0` | Читает логи всех Docker-контейнеров и отправляет в Loki | без портов |

Все три сервиса в общей сети `logging`, поэтому обращаются друг к другу по имени (`http://loki:3100`). Grafana Alloy используется вместо Promtail, поддержку которого Grafana Labs прекратила.

Управление (в папке стека):

```bash
docker compose up -d       # запустить
docker compose ps          # статус — только контейнеры стека, приложение смотрите в docker ps
docker compose logs alloy  # логи сервиса
```

### Отправка логов из приложения

Функция `send_log_to_loki(message, level="info", **labels)` в [app/loki.py](app/loki.py) делает `POST /loki/api/v1/push`:

```json
{"streams": [{"stream": {"app": "server-time", "level": "info", "endpoint": "convert"},
              "values": [["<время в наносекундах>", "Конвертация 15.00 UTC -> 20.00 Asia/Yekaterinburg"]]}]}
```

- Адрес Loki берётся из переменной окружения `LOKI_URL`. Без неё (например, при локальном запуске) функция ничего не отправляет.
- Если Loki недоступен, функция пишет предупреждение и возвращает `False` — приложение продолжает работать.
- `send_log_to_loki_async` делает то же в фоновом потоке, чтобы не задерживать ответ.
- `/convert` отправляет `info` на каждую конвертацию и `warning` на нераспознанное время или пояс; `POST /log` отправляет произвольное сообщение.

Локально с настоящим Loki можно проверить через SSH-туннель:

```bash
ssh -N -L 13100:127.0.0.1:3100 deploy@<сервер> &
LOKI_URL=http://127.0.0.1:13100 .venv/bin/uvicorn app.main:app
```

### Запросы LogQL

| Что показать | Запрос | Legend |
|---|---|---|
| Логи приложения | `{app="server-time"}` или `{container="server-time"}` | — |
| Только предупреждения конвертера | `{app="server-time", endpoint="convert", level="warning"}` | — |
| Распределение по уровню, все контейнеры | `sum by (detected_level) (count_over_time({container=~".+"} [$__range]))` | `{{detected_level}}` |
| Распределение по контейнеру | `sum by (container) (count_over_time({container=~".+"} [$__range]))` | `{{container}}` |
| Распределение по уровню, логи приложения | `sum by (level) (count_over_time({app="server-time"} [$__range]))` | `{{level}}` |

`$__range` — переменная Grafana, равная выбранному периоду дашборда. `detected_level` Loki определяет сам по тексту строки; метку `level` задаёт приложение.

Круговая диаграмма: Dashboards → New → Add visualization → Loki → тип **Pie chart**; запрос в режиме **Code**, в Options — **Type: Instant** и Legend из таблицы; в Value options — **Calculation: Last \***.

## Подготовка сервера

Проверено на Ubuntu 26.04.

1. Установить Docker из официального репозитория Docker (`docker-ce`, `docker-ce-cli`, `containerd.io`, плагины `buildx` и `compose`) и включить автозапуск: `systemctl enable --now docker`.
2. Создать отдельного пользователя для деплоя и дать ему доступ к Docker без `sudo`:
   ```bash
   useradd -m -s /bin/bash deploy
   usermod -aG docker deploy
   ```
3. Сгенерировать для GitHub Actions отдельный ключ без пароля и положить его публичную часть в `/home/deploy/.ssh/authorized_keys`:
   ```bash
   ssh-keygen -t ed25519 -N '' -C 'github-actions-deploy' -f ~/.ssh/test_ci_cd_deploy
   ```
   Приватную часть (`~/.ssh/test_ci_cd_deploy`) записать в секрет `SSH_PRIVATE_KEY`.
4. Открыть порты 8000 (приложение) и 3000 (Grafana), если на сервере или у хостинга включён файрвол.
5. Развернуть стек логирования — см. раздел «Логирование: Loki + Grafana».

Проверка после деплоя:

```bash
ssh deploy@<сервер> 'docker ps'
curl http://<сервер>:8000/health
```

### Рекомендации по безопасности

- Для деплоя используется отдельный пользователь `deploy` с отдельным ключом, root-ключ в GitHub не хранится.
- Стоит отключить вход по паролю и вход под root (`PasswordAuthentication no`, `PermitRootLogin prohibit-password` в `/etc/ssh/sshd_config`), предварительно убедившись, что вход по ключу работает.

## Известные особенности

- Если в окружении задан прокси, который подменяет TLS-сертификаты, `pip install` и `git push` падают с ошибкой `CERTIFICATE_VERIFY_FAILED`. Проверку сертификатов отключать не нужно: запускайте команды без прокси, например `env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy pip install …`.
- Тесты `/date` могут ложно упасть, если запустить их ровно в полночь: дата сменится между ответом сервера и проверкой.
