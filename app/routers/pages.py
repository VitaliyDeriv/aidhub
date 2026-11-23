"""Сторінки-заглушки: публічна головна та домашні сторінки за ролями."""

import socket
from html import escape

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.database import engine
from app.deps import CurrentUser, OptionalUser
from app.models import Role

router = APIRouter(include_in_schema=False)

# Ідентифікатор екземпляра (у Docker — ID контейнера) для перевірки балансування.
INSTANCE = socket.gethostname()

LANDING = """<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><title>AidHub</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:2rem auto;padding:0 1rem}
input,button{display:block;width:100%;margin:.4rem 0;padding:.5rem;box-sizing:border-box}
#msg{color:#b00020}</style></head><body>
<h1>AidHub</h1><p>Координація гуманітарної допомоги між фондами.</p>
<h2>Вхід</h2>
<form id="login"><input name="username" type="email" placeholder="Email" required>
<input name="password" type="password" placeholder="Пароль" required>
<button>Увійти</button></form>
<h2>Реєстрація фонду</h2>
<form id="register"><input name="full_name" placeholder="Ім'я" required>
<input name="fund_name" placeholder="Назва фонду" required>
<input name="email" type="email" placeholder="Email" required>
<input name="password" type="password" minlength="8" placeholder="Пароль (від 8 символів)" required>
<button>Зареєструватися</button></form>
<p id="msg"></p>
<script>
const msg = document.getElementById('msg');
async function login(username, password) {
  const r = await fetch('/api/v1/auth/login', {method: 'POST',
    body: new URLSearchParams({username, password})});
  if (r.ok) { location = '/home'; } else { msg.textContent = 'Невірний email або пароль'; }
}
document.getElementById('login').onsubmit = (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  login(f.get('username'), f.get('password'));
};
document.getElementById('register').onsubmit = async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  const r = await fetch('/api/v1/auth/register', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  if (r.ok) { login(body.email, body.password); }
  else { msg.textContent = r.status === 409 ? 'Email або назва фонду вже зайняті' : 'Перевірте дані форми'; }
};
</script></body></html>"""

HOME = """<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><title>AidHub — {title}</title></head>
<body style="font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem">
<h1>{title}</h1><p>Вітаємо, {name}!</p><p>{hint}</p>
<button onclick="fetch('/api/v1/auth/logout',{{method:'POST'}}).then(()=>location='/')">Вийти</button>
</body></html>"""


@router.get("/", response_class=HTMLResponse)
def landing():
    return LANDING


@router.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "instance": INSTANCE}


@router.get("/home")
def home(user: OptionalUser):
    if user is None:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    target = "/home/admin" if user.role == Role.ADMIN else "/home/user"
    return RedirectResponse(target, status_code=status.HTTP_302_FOUND)


@router.get("/home/user", response_class=HTMLResponse)
def home_user(user: CurrentUser):
    if user.role != Role.USER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This page is for fund users")
    return HOME.format(
        title="Кабінет фонду",
        name=escape(user.full_name),
        hint="Заглушка: тут будуть склади, палети та ваші резервування.",
    )


@router.get("/home/admin", response_class=HTMLResponse)
def home_admin(user: CurrentUser):
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return HOME.format(
        title="Панель адміністратора",
        name=escape(user.full_name),
        hint="Заглушка: керування складами, палетами та користувачами.",
    )
