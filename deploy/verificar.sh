#!/usr/bin/env bash
# Prueba de humo: espera hasta 30 segundos a que /health responda.
URL="${URL_SALUD:-http://localhost:8000/health}"
for _ in $(seq 1 15); do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "Prueba de humo OK ($URL)"
    exit 0
  fi
  sleep 2
done
echo "Prueba de humo FALLIDA ($URL)"
exit 1
