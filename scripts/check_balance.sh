#!/usr/bin/env bash
# Робить N послідовних запитів і показує, який екземпляр відповів.
# Використання: scripts/check_balance.sh [N] [URL]
N="${1:-20}"
URL="${2:-http://localhost/health}"
for i in $(seq 1 "$N"); do
  printf '%2d  ' "$i"
  curl -s -o /dev/null -D - "$URL" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-instance"{print $2}'
done | tee /tmp/balance.out
echo "--- підсумок ---"
awk '{print $2}' /tmp/balance.out | sort | uniq -c
