# Балансування навантаження Nginx (ЛР6)

## Конфігурація

* Три однакові контейнери `web1`, `web2`, `web3` (один образ `aidhub-web`).
* Кожна відповідь має заголовок `X-Instance` (hostname = ID контейнера); `GET /health` повертає його в тілі.
* `nginx/<алгоритм>.conf` містить блок `upstream app_backend`; спільний блок `server` з
  `proxy_pass http://app_backend` — у `nginx/server.inc`.
* Алгоритм обирається `NGINX_CONF` (`round_robin` за замовчуванням).

## Health checks (відмовостійкість)

Nginx OSS має **пасивні** перевірки: `max_fails=2 fail_timeout=10s` виключає сервер на 10 с після
двох невдач, а `proxy_next_upstream error timeout http_502 http_503 http_504` прозоро повторює
запит на іншому сервері. Небезпечні повтори POST не вмикались (`non_idempotent` відсутній), тож
резервування не дублюється; перший запит під час збою може отримати 502, якщо це POST.
Docker healthcheck контейнерів додатково не пускає Nginx стартувати раніше за здорові репліки.

## Перевірка

```bash
docker compose up --build -d
scripts/check_balance.sh 20     # циклічно web1 → web2 → web3 → web1 …
scripts/failover_demo.sh        # stop web2 → увесь трафік лише на web1/web3 → start web2
```

Очікуваний результат Round Robin на 20 запитах: розподіл 7/7/6. Для `weighted` (web1 weight=2): ≈ 10/5/5.
Для `ip_hash` усі запити з одного IP йдуть на одну репліку.

## Додатково: порівняння з одним екземпляром

```bash
NGINX_CONF=single       docker compose up -d nginx   # базова лінія (лише web1)
# locust ... --csv loadtests/results/single
NGINX_CONF=round_robin  docker compose up -d nginx
# locust ... --csv loadtests/results/rr3
```

| Конфігурація | RPS | avg, мс | p95, мс | Error rate |
|---|---|---|---|---|
| 1 екземпляр (`single`) | _ | _ | _ | _ |
| 3 репліки, Round Robin | _ | _ | _ | _ |
| 3 репліки, Least Connections | _ | _ | _ | _ |

Заповніть після прогону. Зауваження: всі репліки спільно використовують одну БД, тому
виграш обмежений там, де вузьке місце — PostgreSQL (блокування «гарячих» палет), а не CPU застосунку.
