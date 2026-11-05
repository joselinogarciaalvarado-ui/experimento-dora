"""Funciones compartidas para registrar mediciones."""
import csv
import os
import re
import subprocess
from pathlib import Path

# En GitHub Codespaces los datos van en /workspaces, que no se borra al reconstruir el entorno.
_BASE = Path("/workspaces") if Path("/workspaces").is_dir() else Path.home()
ARCHIVO_DATOS = Path(os.environ.get("EXPERIMENTO_DATOS", _BASE / "experimento-dora-datos" / "resultados.csv"))

COLUMNAS = [
    "condicion", "cambio", "tipo_registro", "sha", "t_commit", "t_inicio", "t_fin",
    "duracion_s", "lead_time_s", "pasos_manuales", "errores_operador", "resultado", "recuperacion_s",
]


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def datos_commit():
    """Devuelve (sha corto, hora del commit en epoch, número de cambio, tipo de registro)."""
    sha = git("rev-parse", "--short", "HEAD")
    t_commit = float(git("log", "-1", "--format=%ct"))
    mensaje = git("log", "-1", "--format=%s")
    m = re.search(r"cambio (\d+)", mensaje)
    cambio = int(m.group(1)) if m else ""
    tipo = "correccion" if mensaje.lower().startswith("revert") or mensaje.lower().startswith("correccion") else "cambio"
    return sha, t_commit, cambio, tipo


def guardar(fila: dict):
    ARCHIVO_DATOS.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ARCHIVO_DATOS.exists()
    with ARCHIVO_DATOS.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        if nuevo:
            w.writeheader()
        w.writerow({c: fila.get(c, "") for c in COLUMNAS})
    print(f"Registro guardado en {ARCHIVO_DATOS}")
