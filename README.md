# Kit del experimento: despliegue manual vs. CI/CD vs. CI/CD + DevSecOps

Este kit sirve para medir las cinco métricas DORA en tres formas de desplegar la misma aplicación:

| Condición | Cómo se despliega |
| --- | --- |
| **A. Manual** | Tú construyes y levantas el contenedor a mano, guiado por `scripts/cronometro_manual.py` |
| **B. CI/CD** | GitHub Actions corre pruebas, construye, despliega, verifica y hace *rollback* si algo falla |
| **C. CI/CD + DevSecOps** | Igual que B, más Bandit, pip-audit, Gitleaks y Trivy |

Todo es gratuito. Los datos quedan en `experimento-dora-datos/resultados.csv`: en Codespaces dentro de `/workspaces/`, y en Ubuntu dentro de tu carpeta personal.

---

## Opción recomendada: GitHub Codespaces (en la nube, sin instalar nada)

Codespaces es una computadora Linux en la nube que se abre en el navegador. El plan gratuito incluye 60 horas al mes en una máquina de 2 núcleos; el experimento usa unas 12.

**Antes de empezar:** en GitHub ve a **Settings → Codespaces → Default idle timeout** y pon **120** minutos.

1. **Crea el repositorio:** en GitHub, **New repository** → nombre `experimento-dora` → **Private** → marca **Add a README file** → **Create repository**.
2. **Abre el Codespace:** en el repositorio, botón verde **Code** → pestaña **Codespaces** → **Create codespace on main**. Se abre VS Code en tu navegador.
3. **Sube el kit:** arrastra `experimento-dora.zip` al panel de archivos de la izquierda.
4. **Descomprime y guarda la versión base.** En la terminal de abajo, pega:

```bash
unzip -q experimento-dora.zip && cp -r experimento-dora/. . && rm -rf experimento-dora experimento-dora.zip
git add -A && git commit -m "version base" && git tag base && git push && git push --tags
```

5. **Prepara el entorno**, una sola vez y en unos 5 a 10 minutos:

```bash
bash scripts/preparar_entorno.sh
```

Debe terminar con **LISTO**.

6. **Instala el runner de GitHub dentro del Codespace:** en otra pestaña del navegador abre tu repositorio → **Settings → Actions → Runners → New self-hosted runner → Linux / x64**. Copia los comandos de las secciones *Download* y *Configure* y pégalos en una **terminal nueva** del Codespace (en VS Code, el ícono **+** de la terminal). Acepta las opciones por defecto con Enter. Al final ejecuta `./run.sh` y deja esa terminal abierta.
7. **Crea la variable `CONDICION`** (sección 5 de este README) y sigue desde la **sección 7**.

**Al terminar cada sesión:** descarga `/workspaces/experimento-dora-datos/resultados.csv` (clic derecho → *Download*) como respaldo. Luego detén el Codespace en **github.com/codespaces** → **⋯ → Stop codespace**, para no gastar horas gratuitas. Cuando vuelvas, ábrelo desde la misma página, entra a la carpeta del runner y ejecuta `./run.sh` otra vez.

---

## Opción alternativa: tu propia computadora con Ubuntu

## 1. Requisitos

- Una computadora con **Ubuntu 22.04 o 24.04**. En Windows usa **WSL2 con Ubuntu** y Docker Desktop con la integración de WSL activada.
- **Docker**, **Git**, **Python 3.12 o superior** y `curl`.
- Una cuenta gratuita de **GitHub**.

Antes de empezar, anota las características del equipo (se reportan en el artículo):

```bash
lscpu | grep "Model name"; free -h | grep Mem; docker version --format '{{.Server.Version}}'; python3 --version; git --version
```

## 2. Preparar el repositorio

1. Crea un repositorio **privado** en GitHub llamado `experimento-dora`.
2. En la carpeta del kit:

```bash
git init -b main
git add -A
git commit -m "version base"
git tag base
git remote add origin https://github.com/TU_USUARIO/experimento-dora.git
git push -u origin main --tags
```

## 3. Preparar el entorno (una sola vez)

```bash
python3 -m venv ~/venv-experimento
~/venv-experimento/bin/pip install -r requirements-dev.txt
mkdir -p ~/.cache/trivy ~/experimento-dora-datos
docker pull python:3.12-slim
docker pull ghcr.io/gitleaks/gitleaks:latest
docker pull aquasec/trivy:latest
# Descarga la base de datos de Trivy para que no se cuente en el tiempo del experimento:
docker run --rm -v "$HOME/.cache/trivy:/root/.cache/" aquasec/trivy:latest image --download-db-only
```

Comprueba que las pruebas pasan: `~/venv-experimento/bin/python -m pytest -q`

## 4. Instalar el runner de GitHub en tu computadora

1. En GitHub: **Settings → Actions → Runners → New self-hosted runner → Linux**.
2. Copia y ejecuta los comandos que te muestra GitHub (descargar, `./config.sh`, `./run.sh`).
3. Tu usuario debe poder usar Docker sin `sudo`: `sudo usermod -aG docker $USER` y vuelve a iniciar sesión.
4. Deja `./run.sh` abierto en una terminal mientras corres las condiciones B y C.

## 5. Crear la variable que elige la condición

En GitHub: **Settings → Secrets and variables → Actions → Variables → New repository variable**

- Nombre: `CONDICION`
- Valor: `A` para empezar

## 6. Levantar la versión base

Así existe una versión anterior a la cual volver si un despliegue falla:

```bash
docker build -t solicitudes:base .
docker run -d --name solicitudes -p 8000:8000 -v solicitudes-datos:/srv/datos solicitudes:base
curl http://localhost:8000/health
```

**Antes de empezar la condición A, comprueba que la versión base pasa todos los controles de seguridad**, porque si no, la condición C bloquearía todos los cambios:

```bash
~/venv-experimento/bin/bandit -r app -ll -q
~/venv-experimento/bin/pip-audit -r requirements.txt
docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:latest dir /repo --no-banner
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$HOME/.cache/trivy:/root/.cache/" \
  aquasec/trivy:latest image --pkg-types library --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 solicitudes:base
```

Si Trivy reporta paquetes de la imagen base (por ejemplo `pip` o `setuptools`), agrega al `Dockerfile`, antes de `COPY requirements.txt .`, la línea `RUN pip install --no-cache-dir --upgrade pip setuptools`. Si pip-audit reporta algo en `requirements.txt`, sube esa versión. Después haz commit, mueve la etiqueta (`git tag -f base && git push --force --tags`) y repite la revisión. **Todo esto se hace una sola vez, antes de la condición A.**

## 7. Ejecutar el experimento

Sigue el orden de `cambios/orden.csv` (30 pasos). La columna `tipo` te dice si el cambio es normal o tiene un defecto. **Es el mismo orden en las tres condiciones.**

### Condición A (manual)

Con `CONDICION = A`, para cada paso de `orden.csv`:

```bash
python3 scripts/aplicar_cambio.py N          # N = número de cambio de esa fila
git add -A && git commit -m "cambio NN: ..."  # copia el mensaje que imprime el script
git push
python3 scripts/cronometro_manual.py         # despliegas a mano siguiendo las instrucciones
```

Si el cambio **no es normal** (tiene un defecto), después de desplegarlo haz la corrección:

```bash
git revert --no-edit HEAD && git push
python3 scripts/cronometro_manual.py         # despliegue correctivo
```

### Condiciones B y C (automatizadas)

1. Cambia la variable `CONDICION` a `B` (luego a `C`).
2. Vuelve a la versión base:

```bash
git checkout main && git reset --hard base && git push --force
```

3. Espera a que termine el pipeline de esa versión base en la pestaña **Actions**.
4. Para cada paso de `orden.csv`:

```bash
python3 scripts/aplicar_cambio.py N
git add -A && git commit -m "cambio NN: ..."
git push
```

5. **Espera a que el pipeline termine** antes del siguiente paso. Así la cola no infla los tiempos.
6. Si el cambio **no es normal**, haz la corrección y espera de nuevo:

```bash
git revert --no-edit HEAD && git push
```

El último job del pipeline (`registrar`) guarda la medición automáticamente.

## 8. Analizar

```bash
~/venv-experimento/bin/python scripts/analizar.py
```

Se crea la carpeta `resultados/` con el resumen por condición, las pruebas estadísticas y dos gráficas.

## Tiempo estimado

| Condición | Despliegues | Tiempo aproximado |
| --- | --- | --- |
| A. Manual | 30 cambios + 12 correcciones | 4 a 5 horas |
| B. CI/CD | 30 cambios + 12 correcciones | 2 a 3 horas |
| C. CI/CD + DevSecOps | 30 cambios + 12 correcciones | 3 a 4 horas |

Puedes repartirlo en varios días; los datos se acumulan en el mismo archivo.

## Reglas para que los datos sean válidos

- No cambies el orden de los cambios ni te saltes ninguno.
- No edites `resultados.csv` a mano. Si un registro sale mal por un error tuyo ajeno al experimento (por ejemplo, se fue la luz), anótalo en una bitácora aparte y explícalo en el artículo.
- Usa la misma computadora y no corras otros programas pesados durante las mediciones.
- El token que crea el cambio 29 es **ficticio**; está ahí para que Gitleaks lo detecte.
