#!/usr/bin/env bash
# Despliegue automatizado con verificación y rollback (condiciones B y C).
# Uso: bash deploy/desplegar.sh solicitudes:<sha>
# Escribe en $GITHUB_OUTPUT: resultado=desplegado|fallo_humo y recuperacion_s=<segundos>
set -u
IMAGEN="$1"
NOMBRE="solicitudes"
DIR="$(cd "$(dirname "$0")" && pwd)"
SALIDA="${GITHUB_OUTPUT:-/dev/stdout}"

ANTERIOR="$(docker inspect --format '{{.Config.Image}}' "$NOMBRE" 2>/dev/null || true)"
echo "Imagen anterior: ${ANTERIOR:-ninguna}"

levantar() {
  docker rm -f "$NOMBRE" >/dev/null 2>&1 || true
  docker run -d --name "$NOMBRE" -p 8000:8000 -v solicitudes-datos:/srv/datos "$1" >/dev/null
}

levantar "$IMAGEN"
if bash "$DIR/verificar.sh"; then
  echo "resultado=desplegado" >> "$SALIDA"
  echo "recuperacion_s=" >> "$SALIDA"
  exit 0
fi

# Falla detectada: rollback a la versión anterior y medición del tiempo de recuperación.
T0=$(date +%s.%N)
echo "Registros del contenedor fallido:"; docker logs "$NOMBRE" 2>&1 | tail -20
if [ -n "$ANTERIOR" ]; then
  levantar "$ANTERIOR"
  bash "$DIR/verificar.sh" || echo "ATENCIÓN: el rollback tampoco respondió"
fi
T1=$(date +%s.%N)
echo "resultado=fallo_humo" >> "$SALIDA"
echo "recuperacion_s=$(python3 -c "print(round($T1 - $T0, 1))")" >> "$SALIDA"
exit 0
