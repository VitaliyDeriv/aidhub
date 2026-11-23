# Навантажувальне тестування (ЛР4)

Інструмент: **Locust** (сценарій на Python, легко моделює авторизованого користувача).

## Цільові ендпоінти

| Ендпоінт | Вага | Навіщо |
|---|---|---|
| `GET /` | 1 | статична сторінка, базова лінія |
| `POST /api/v1/auth/login`, `/register` | 1 раз на користувача | hash-ємна операція (scrypt, CPU) |
| `GET /api/v1/pallets?status=available` | 5 | типове читання каталогу |
| `POST /api/v1/reservations` (hot) | 3 | конкуренція за 200 «гарячих» палет → блокування рядків, 409 |
| `POST /api/v1/reservations` (cold) | 2 | запис без конфліктів |
| `GET /api/v1/reservations` | 2 | читання своїх бронювань |
| `DELETE /api/v1/reservations/{id}` | 1 | скасування |

Відповідь 409 у сценарії рахується **очікуваною** (палета вже зайнята), а не помилкою.

## Початковий профіль

| Параметр | Значення |
|---|---|
| Віртуальні користувачі | 50 |
| Ramp-up | 5 користувачів/с (≈10 с) |
| Тривалість | 3 хв |
| Пауза між діями | 1–3 с |
| Палет у пулі | 5000 (200 «гарячих») |

## Запуск

```bash
docker compose up --build -d
mkdir -p loadtests/results
ADMIN_PASSWORD='<з .env>' locust -f loadtests/locustfile.py --host http://localhost \
  --headless -u 50 -r 5 -t 3m --csv loadtests/results/run1 --html loadtests/results/run1.html
docker stats --no-stream      # зняти CPU/RAM контейнерів під час піка (окремим вікном: `docker stats`)
```

## Шаблон звіту (заповнити фактичними результатами запуску)

| Метрика | Значення |
|---|---|
| RPS (середній / пік) | _ |
| Latency avg / min / max, мс | _ |
| Latency p95, мс | _ |
| Error rate (без 409), % | _ |
| CPU web / db, % | _ |
| RAM web / db, MiB | _ |

Графіки (з `run1.html` Locust): Total Requests per Second, Response Times (p50/p95), Number of Users.

### Вузькі місця, які варто перевірити

1. **scrypt при логіні/реєстрації** — CPU-bound, при хвилі входів різко зростає latency; слід дивитися p95 `/auth/login`.
2. **Блокування рядків на «гарячих» палетах** — зростання p95 `POST /reservations (hot)` зі збільшенням користувачів.
3. **Пул з'єднань SQLAlchemy** (`pool_size=5`, `max_overflow=10`) на репліку — при вичерпанні запити чекають.
4. **Читання `/pallets` без кешу** — кандидат на Redis.

> Цифри в цьому репозиторії не заповнені навмисно: їх треба зняти на вашій машині/середовищі.
