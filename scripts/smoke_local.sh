#!/usr/bin/env bash

set -u

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ADMIN_DOCUMENTO="${ADMIN_DOCUMENTO:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
USER_TOKEN="${USER_TOKEN:-}"

echo "Smoke local against: ${BASE_URL}"

echo
echo "== GET /"
curl -sS -i "${BASE_URL}/"
echo

echo
echo "== GET /docs"
curl -sS -o /dev/null -w "HTTP %{http_code} ${BASE_URL}/docs\n" "${BASE_URL}/docs"

echo
echo "== GET /subastas/publicas"
curl -sS -i "${BASE_URL}/subastas/publicas"
echo

if [[ -n "${ADMIN_DOCUMENTO}" && -n "${ADMIN_PASSWORD}" ]]; then
  echo
  echo "== POST /auth/login"
  curl -sS -i -X POST "${BASE_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"documento\":\"${ADMIN_DOCUMENTO}\",\"password\":\"${ADMIN_PASSWORD}\"}"
  echo
else
  echo
  echo "== POST /auth/login skipped"
  echo "Set ADMIN_DOCUMENTO and ADMIN_PASSWORD to run the login smoke."
fi

if [[ -n "${USER_TOKEN}" ]]; then
  echo
  echo "== GET /usuarios/me"
  curl -sS -i "${BASE_URL}/usuarios/me" \
    -H "Authorization: Bearer ${USER_TOKEN}"
  echo
else
  echo
  echo "== GET /usuarios/me skipped"
  echo "Set USER_TOKEN to run the authenticated profile smoke."
fi
