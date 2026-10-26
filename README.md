# Server Time API

Учебный бэкенд на FastAPI: показывает текущее время сервера и переводит время из UTC в другие часовые пояса. На примере проекта настроен CI/CD: GitHub Actions собирает Docker-образ, публикует его в GitHub Container Registry и разворачивает на сервере по SSH.

## Возможности

- Веб-страница на `/`: часы сервера, дата, часовой пояс, номер недели, прогресс года и конвертер времени из UTC с подсказками городов.
- JSON API с текущим временем, датой и конвертацией между часовыми поясами.
- Автоматическая сборка и деплой при каждом push в `main`.

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
2. **Deploy to server** — по SSH заходит на сервер, скачивает образ с тегом текущего коммита и перезапускает контейнер `server-time` на порту 8000 (`--restart unless-stopped`).

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
4. Открыть порт 8000, если на сервере или у хостинга включён файрвол.

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
