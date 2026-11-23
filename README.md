# AidHub — платформа координації гуманітарної допомоги

Фонди резервують палети з гуманітарною допомогою на складах. Ключова вимога —
**жодна палета не може бути заброньована двічі**, навіть якщо кілька фондів
одночасно надсилають конкуруючі запити.

Стек: FastAPI · SQLAlchemy 2 · PostgreSQL 16 · JWT · Docker Compose · Nginx · Locust · pytest · ruff.

## Швидкий старт (Docker, одна команда)

```bash
cp .env.example .env            # змініть SECRET_KEY, паролі
docker compose up --build       # БД + 3 репліки + Nginx на http://localhost
```

* Сайт: <http://localhost/> (форма входу/реєстрації), `GET /health` показує, яка репліка відповіла.
* API: `/api/v1/...` (Swagger `/docs` лише при `DEBUG=true`).
* Дані PostgreSQL зберігаються у volume `pgdata` і переживають `docker compose down`
  (видалити разом з даними: `docker compose down -v`).
* Адміністратор створюється при старті з `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

Hot-reload для розробки (bind mount коду, `uvicorn --reload`):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Запуск без Docker у двох середовищах (ЛР3)

Конфігурація читається зі змінних оточення та файлу `.env.<APP_ENV>`
(`pydantic-settings`). Реальні змінні мають пріоритет над файлом.

| | Sandbox | Production |
|---|---|---|
| Файл | `.env.sandbox` | `.env.production` |
| База | `aidhub_sandbox` | `aidhub_production` (окрема БД) |
| DEBUG | може бути `true` | примусово `false` (застосунок не стартує з `true`) |
| Swagger `/docs` | при DEBUG | вимкнений |
| SECRET_KEY | будь-який ≥16 символів | унікальний; відомі слабкі значення відхиляються |

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.sandbox.example .env.sandbox        # відредагуйте значення
APP_ENV=sandbox uvicorn app.main:app --reload

cp .env.production.example .env.production  # відредагуйте значення
APP_ENV=production uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Помилки 500 клієнт бачить як `{"detail": "Internal server error"}`; стектрейс іде лише в лог.
Файли `.env*` (крім `*.example`) у git не потрапляють.

## Ролі та доступ (ЛР2)

| Роль | Можливості |
|---|---|
| `user` (представник фонду) | реєстрація, вхід, перегляд складів/палет, резервування й скасування **лише для свого фонду**, редагування лише власного профілю |
| `admin` | усе вище для будь-яких даних + `/api/v1/admin/*` (склади, палети, користувачі, статистика) |

* Реєстрація створює завжди роль `user` і новий фонд; поле `role` у запиті ігнорується.
* Вхід: `POST /api/v1/auth/login` (форма `username` = email, `password`) → JWT у відповіді та httpOnly-cookie.
* Сторінки: `/` (вхід), `/home` → `/home/user` або `/home/admin`.
* Без авторизації — `401` (для `/home` — `302` на `/`), чужа роль — `403`, чужий ресурс (IDOR) — `403`.

## Тести та якість коду

```bash
pytest                       # юніт та інтеграційні тести (in-memory SQLite)
ruff check . && ruff format --check .
pre-commit install           # хуки блокують коміт із помилками стилю/синтаксису
```

Покриття: анонімний доступ (401/302), успішний вхід і помилки входу, вертикальне розмежування
(403 для user на admin), IDOR на профілі та резервуваннях, атомарність і подвійне бронювання.

## Балансування навантаження (ЛР6)

Три репліки `web1..web3` за Nginx. Алгоритм вибирається змінною `NGINX_CONF`
(`round_robin` за замовчуванням, `least_conn`, `weighted`, `ip_hash`, `single`):

```bash
NGINX_CONF=least_conn docker compose up -d nginx
scripts/check_balance.sh 20          # 20 запитів, видно X-Instance кожної відповіді
scripts/failover_demo.sh             # зупиняє web2, показує, що трафік іде на web1/web3
```

Деталі й таблиця для звіту: [docs/load-balancing.md](docs/load-balancing.md).

## Навантажувальне тестування (ЛР4)

```bash
pip install -r requirements-dev.txt
ADMIN_PASSWORD=... locust -f loadtests/locustfile.py --host http://localhost \
  --headless -u 50 -r 5 -t 3m --csv loadtests/results/run1 --html loadtests/results/run1.html
```

План, профіль і шаблон звіту: [docs/load-testing.md](docs/load-testing.md).

## Документація

* [docs/architecture.md](docs/architecture.md) — вибір предметної області, схема, обґрунтування рішень.
* [docs/load-testing.md](docs/load-testing.md), [docs/load-balancing.md](docs/load-balancing.md).

## Структура

```
app/            FastAPI: config, models, security, deps, routers/, services/
tests/          pytest
loadtests/      сценарій Locust
nginx/          конфіги балансувальника
scripts/        демонстрація балансування й відмовостійкості
docs/           архітектура та звіти
.github/        CI (ruff + pytest + docker build)
```
