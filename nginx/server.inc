server {
    listen 80;
    server_tokens off;

    location / {
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Пасивний health check: при збої з'єднання, таймауті чи 502/503/504
        # запит повторюється на іншому сервері. POST не повторюємо автоматично
        # (non_idempotent не вказано), щоб не продублювати резервування.
        proxy_next_upstream error timeout http_502 http_503 http_504;
        proxy_next_upstream_tries 3;
        proxy_connect_timeout 2s;
        proxy_read_timeout 30s;
    }
}
