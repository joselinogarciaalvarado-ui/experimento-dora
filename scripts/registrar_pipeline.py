#!/usr/bin/env python3
"""Lo ejecuta el último job del pipeline (condiciones B y C) para guardar la medición."""
import os
import time

from comun import datos_commit, guardar


def resultado():
    if os.environ.get("R_PRUEBAS") != "success":
        return "bloqueado_pruebas"
    if os.environ.get("R_SEGURIDAD") == "failure" or os.environ.get("R_ESCANEO") == "failure":
        return "bloqueado_seguridad"
    if os.environ.get("R_CONSTRUIR") != "success":
        return "error_construccion"
    return os.environ.get("R_DESPLIEGUE") or "error_despliegue"


def main():
    t_fin = time.time()
    sha, t_commit, cambio, tipo = datos_commit()
    t_inicio = float(os.environ["T_INICIO"])
    guardar({
        "condicion": os.environ["CONDICION"],
        "cambio": cambio,
        "tipo_registro": tipo,
        "sha": sha,
        "t_commit": f"{t_commit:.0f}",
        "t_inicio": f"{t_inicio:.3f}",
        "t_fin": f"{t_fin:.3f}",
        "duracion_s": f"{t_fin - t_inicio:.1f}",
        "lead_time_s": f"{t_fin - t_commit:.1f}",
        "pasos_manuales": 2,  # commit y push
        "errores_operador": 0,
        "resultado": resultado(),
        "recuperacion_s": os.environ.get("RECUPERACION_S", ""),
    })


if __name__ == "__main__":
    main()
