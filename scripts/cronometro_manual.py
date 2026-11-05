#!/usr/bin/env python3
"""Guía y cronometra un despliegue MANUAL (condición A).

Uso (después de hacer commit del cambio):
    python3 scripts/cronometro_manual.py

El script muestra cada paso. Ejecuta el comando en OTRA terminal y vuelve aquí:
    Enter = paso terminado    r = tuve que repetir el paso (error del operador)
"""
import subprocess
import time

from comun import datos_commit, guardar

NOMBRE = "solicitudes"


def imagen_actual():
    r = subprocess.run(["docker", "inspect", "--format", "{{.Config.Image}}", NOMBRE], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def ejecutar_pasos(pasos):
    """Muestra cada paso, espera confirmación y devuelve (pasos realizados, errores)."""
    realizados, errores = 0, 0
    for i, (desc, cmd) in enumerate(pasos, 1):
        print(f"\nPaso {i}/{len(pasos)}: {desc}\n    {cmd}")
        while True:
            r = input("  [Enter] listo  |  [r] lo repetí por un error > ").strip().lower()
            realizados += 1
            if r == "r":
                errores += 1
                continue
            break
    return realizados, errores


def main():
    sha, t_commit, cambio, tipo = datos_commit()
    anterior = imagen_actual()
    nueva = f"{NOMBRE}:{sha}"
    print(f"Despliegue manual del commit {sha} (cambio {cambio or '-'}, {tipo}).")
    print(f"Imagen actual en producción: {anterior or 'ninguna'}")
    input("\nCuando estés listo para empezar, presiona Enter (aquí empieza el cronómetro)...")
    t_inicio = time.time()

    pasos = [
        ("Construir la imagen", f"docker build --build-arg APP_VERSION={sha} -t {nueva} ."),
        ("Detener y quitar el contenedor actual", f"docker rm -f {NOMBRE}"),
        ("Levantar el contenedor nuevo",
         f"docker run -d --name {NOMBRE} -p 8000:8000 -v solicitudes-datos:/srv/datos {nueva}"),
        ("Verificar que responde (repite si hace falta)", "curl -fsS http://localhost:8000/health"),
    ]
    realizados, errores = ejecutar_pasos(pasos)
    ok = input("\n¿La verificación respondió con estado ok? [s/n] > ").strip().lower() == "s"
    t_fin = time.time()

    recuperacion = ""
    resultado = "desplegado"
    if not ok:
        resultado = "fallo_humo"
        print("\nFalla detectada. Haz el rollback manual a la versión anterior.")
        t0 = time.time()
        r2, e2 = ejecutar_pasos([
            ("Quitar el contenedor fallido", f"docker rm -f {NOMBRE}"),
            ("Levantar la versión anterior",
             f"docker run -d --name {NOMBRE} -p 8000:8000 -v solicitudes-datos:/srv/datos {anterior}"),
            ("Verificar que responde", "curl -fsS http://localhost:8000/health"),
        ])
        input("Cuando la versión anterior responda ok, presiona Enter...")
        recuperacion = f"{time.time() - t0:.1f}"
        realizados += r2
        errores += e2

    guardar({
        "condicion": "A",
        "cambio": cambio,
        "tipo_registro": tipo,
        "sha": sha,
        "t_commit": f"{t_commit:.0f}",
        "t_inicio": f"{t_inicio:.3f}",
        "t_fin": f"{t_fin:.3f}",
        "duracion_s": f"{t_fin - t_inicio:.1f}",
        "lead_time_s": f"{t_fin - t_commit:.1f}",
        "pasos_manuales": realizados + 1,  # más el commit
        "errores_operador": errores,
        "resultado": resultado,
        "recuperacion_s": recuperacion,
    })


if __name__ == "__main__":
    main()
