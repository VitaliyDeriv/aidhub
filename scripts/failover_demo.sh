#!/usr/bin/env bash
# Демонстрація відмовостійкості: зупиняє web2 і перевіряє, що весь трафік іде на решту.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== До збою =="; scripts/check_balance.sh 12
echo "== Зупиняємо web2 =="; docker compose stop web2
echo "== Після збою (жодної помилки, лише web1/web3) =="; scripts/check_balance.sh 12
echo "== Відновлюємо web2 =="; docker compose start web2
sleep 15
echo "== Після відновлення =="; scripts/check_balance.sh 12
