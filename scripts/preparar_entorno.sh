#!/usr/bin/env bash
# Prepara el entorno del experimento (GitHub Codespaces o Ubuntu). Ejecutar una sola vez:
#   bash scripts/preparar_entorno.sh
set -e
cd "$(dirname "$0")/.."

echo "== 1/6 Registrando el equipo (guárdalo para el artículo) =="
DATOS="${EXPERIMENTO_DATOS_DIR:-$([ -d /workspaces ] && echo /workspaces/experimento-dora-datos || echo "$HOME/experimento-dora-datos")}"
mkdir -p "$DATOS" "$HOME/.cache/trivy"
{
  echo "Fecha: $(date -Iseconds)"
  echo "CPU: $(lscpu | grep 'Model name' | sed 's/Model name:\s*//')"
  echo "Núcleos: $(nproc)"
  echo "Memoria: $(free -h | awk '/Mem:/ {print $2}')"
  echo "Docker: $(docker version --format '{{.Server.Version}}')"
  echo "Python: $(python3 --version)"
  echo "Git: $(git --version)"
} | tee "$DATOS/equipo.txt"

echo "== 2/6 Creando el entorno de Python =="
python3 -m venv "$HOME/venv-experimento"
"$HOME/venv-experimento/bin/pip" install -q --upgrade pip
"$HOME/venv-experimento/bin/pip" install -q -r requirements-dev.txt

echo "== 3/6 Descargando imágenes de Docker =="
docker pull -q python:3.12-slim
docker pull -q ghcr.io/gitleaks/gitleaks:latest
docker pull -q aquasec/trivy:latest
docker run --rm -v "$HOME/.cache/trivy:/root/.cache/" aquasec/trivy:latest image --download-db-only

echo "== 4/6 Corriendo las pruebas =="
"$HOME/venv-experimento/bin/python" -m pytest -q -p no:cacheprovider

echo "== 5/6 Construyendo y levantando la versión base =="
docker build -q -t solicitudes:base .
docker rm -f solicitudes >/dev/null 2>&1 || true
docker run -d --name solicitudes -p 8000:8000 -v solicitudes-datos:/srv/datos solicitudes:base >/dev/null
bash deploy/verificar.sh

echo "== 6/6 Revisando que la versión base pasa los controles de seguridad =="
FALLAS=0
"$HOME/venv-experimento/bin/bandit" -r app -ll -q || FALLAS=1
"$HOME/venv-experimento/bin/pip-audit" -r requirements.txt --progress-spinner off || FALLAS=1
docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:latest dir /repo --no-banner || FALLAS=1
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$HOME/.cache/trivy:/root/.cache/" \
  aquasec/trivy:latest image --pkg-types library --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 solicitudes:base || FALLAS=1

echo
if [ "$FALLAS" -eq 0 ]; then
  echo "LISTO: el entorno está preparado y la versión base pasa todos los controles."
  echo "Los datos se guardarán en: $DATOS/resultados.csv"
else
  echo "ATENCIÓN: algún control de seguridad falló con la versión base."
  echo "Copia el mensaje de arriba y compártelo para ajustar la versión base antes de empezar."
fi
