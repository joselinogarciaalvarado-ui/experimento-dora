#!/usr/bin/env python3
"""Aplica uno de los 30 cambios predefinidos del experimento.

Uso:
    python scripts/aplicar_cambio.py 17          # aplica el cambio 17 al código
    python scripts/aplicar_cambio.py --catalogo  # regenera cambios/catalogo.csv
    python scripts/aplicar_cambio.py --orden     # regenera cambios/orden.csv (semilla fija)

Después de aplicar el cambio, haz commit con el mensaje exacto que imprime el script.
"""
import csv
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SEMILLA = 2026

NORMAL = "normal"
DEF_PRUEBAS = "defecto_pruebas"
DEF_HUMO = "defecto_humo"
DEF_SEGURIDAD = "defecto_seguridad"


def _carrera(cod, nombre):
    return [
        ("append", "app/catalogo.py", f'\nCARRERAS["{cod}"] = "{nombre}"\n'),
        ("append", "tests/test_cambios.py", f'\n\ndef test_carrera_{cod.lower()}():\n    assert CARRERAS["{cod}"] == "{nombre}"\n'),
    ]


def _tipo(nombre, base):
    return [
        ("append", "app/catalogo.py", f'\nTIPOS["{nombre}"] = {base}\n'),
        ("append", "tests/test_cambios.py",
         f'\n\ndef test_tipo_{nombre}():\n    from app.reglas import calcular_prioridad\n'
         f'    assert calcular_prioridad("{nombre}", 0) == {base}\n'),
    ]


def _ruta(codigo, prueba):
    return [("append", "app/main.py", codigo), ("append", "tests/test_cambios.py", prueba)]


CAMBIOS = {
    # --- 18 cambios normales -------------------------------------------------
    1: (NORMAL, "Agregar carrera Ingeniería Industrial", _carrera("II", "Ingeniería Industrial")),
    2: (NORMAL, "Agregar carrera Ingeniería Civil", _carrera("IC", "Ingeniería Civil")),
    3: (NORMAL, "Agregar carrera Administración de Empresas", _carrera("AE", "Administración de Empresas")),
    4: (NORMAL, "Agregar carrera Contaduría Pública", _carrera("CP", "Contaduría Pública")),
    5: (NORMAL, "Agregar carrera Economía", _carrera("EC", "Economía")),
    6: (NORMAL, "Agregar carrera Mercadotecnia", _carrera("MK", "Mercadotecnia")),
    7: (NORMAL, "Agregar carrera Comercio Internacional", _carrera("CI", "Comercio Internacional")),
    8: (NORMAL, "Agregar carrera Banca y Finanzas", _carrera("BF", "Banca y Finanzas")),
    9: (NORMAL, "Agregar tipo reposición de examen", _tipo("reposicion_examen", 6)),
    10: (NORMAL, "Agregar tipo equivalencias", _tipo("equivalencias", 4)),
    11: (NORMAL, "Agregar tipo retiro de asignatura", _tipo("retiro_asignatura", 5)),
    12: (NORMAL, "Agregar tipo beca", _tipo("beca", 7)),
    13: (NORMAL, "Agregar tipo trámite de título", _tipo("titulo", 8)),
    14: (NORMAL, "Ruta GET /carreras", _ruta(
        '\n\n@app.get("/carreras")\ndef listar_carreras():\n    return CARRERAS\n',
        '\n\ndef test_ruta_carreras(cliente):\n    assert "IA" in cliente.get("/carreras").json()\n')),
    15: (NORMAL, "Ruta GET /tipos", _ruta(
        '\n\n@app.get("/tipos")\ndef listar_tipos():\n    return TIPOS\n',
        '\n\ndef test_ruta_tipos(cliente):\n    assert "constancia" in cliente.get("/tipos").json()\n')),
    16: (NORMAL, "Ruta GET /estadisticas", _ruta(
        '\n\n@app.get("/estadisticas")\ndef estadisticas():\n    with conectar() as con:\n'
        '        filas = con.execute("SELECT tipo, COUNT(*) AS total FROM solicitudes GROUP BY tipo").fetchall()\n'
        '    return {f["tipo"]: f["total"] for f in filas}\n',
        '\n\ndef test_ruta_estadisticas(cliente):\n    assert cliente.get("/estadisticas").status_code == 200\n')),
    17: (NORMAL, "Ruta GET /version", _ruta(
        '\n\n@app.get("/version")\ndef version():\n    return {"version": VERSION, "entorno": ENTORNO}\n',
        '\n\ndef test_ruta_version(cliente):\n    assert "version" in cliente.get("/version").json()\n')),
    18: (NORMAL, "Ruta GET /solicitudes/cuenta/{cuenta}", _ruta(
        '\n\n@app.get("/solicitudes/cuenta/{cuenta}")\ndef solicitudes_por_cuenta(cuenta: str):\n'
        '    with conectar() as con:\n'
        '        filas = con.execute("SELECT * FROM solicitudes WHERE cuenta = ?", (cuenta,)).fetchall()\n'
        '    return [dict(f) for f in filas]\n',
        '\n\ndef test_ruta_por_cuenta(cliente):\n    assert cliente.get("/solicitudes/cuenta/00000000").json() == []\n')),
    # --- 6 defectos que detectan las pruebas unitarias ----------------------
    19: (DEF_PRUEBAS, "Prioridad: se pierde el cálculo por semanas de espera",
         [("replace", "app/reglas.py", "extra = dias_espera // 7", "extra = 0")]),
    20: (DEF_PRUEBAS, "Prioridad: se elimina el tope máximo",
         [("replace", "app/reglas.py", "return min(base + extra, PRIORIDAD_MAXIMA)", "return base + extra")]),
    21: (DEF_PRUEBAS, "Validación de carrera distingue mayúsculas",
         [("replace", "app/reglas.py", "return codigo.upper() in CARRERAS", "return codigo in CARRERAS")]),
    22: (DEF_PRUEBAS, "Crear solicitud deja de responder 201",
         [("replace", "app/main.py", '@app.post("/solicitudes", status_code=201)', '@app.post("/solicitudes")')]),
    23: (DEF_PRUEBAS, "Se aceptan días de espera negativos",
         [("replace", "app/main.py", "if datos.dias_espera < 0:", "if datos.dias_espera < -9999:")]),
    24: (DEF_PRUEBAS, "Solicitud inexistente devuelve vacío en lugar de 404",
         [("replace", "app/main.py", '        raise HTTPException(status_code=404, detail="Solicitud no encontrada")',
           "        return {}")]),
    # --- 3 defectos que solo detecta la prueba de humo ----------------------
    25: (DEF_HUMO, "Ruta de la base de datos inexistente en el contenedor",
         [("replace", "Dockerfile", "DB_PATH=/srv/datos/solicitudes.db", "DB_PATH=/srv/no_existe/solicitudes.db")]),
    26: (DEF_HUMO, "El contenedor escucha en un puerto equivocado",
         [("replace", "Dockerfile", '"--port", "8000"', '"--port", "9000"')]),
    27: (DEF_HUMO, "Variable de entorno obligatoria ausente en producción",
         [("replace", "app/main.py", 'ENTORNO = os.environ.get("ENTORNO", "desarrollo")',
           'ENTORNO = os.environ.get("ENTORNO", "desarrollo")\n'
           'CLAVE_SESION = os.environ["CLAVE_SESION"] if ENTORNO == "produccion" else "clave-desarrollo"')]),
    # --- 3 defectos de seguridad --------------------------------------------
    28: (DEF_SEGURIDAD, "Dependencia con vulnerabilidades conocidas (Jinja2 2.10)",
         [("append", "requirements.txt", "jinja2==2.10\n")]),
    29: (DEF_SEGURIDAD, "Token de acceso escrito en el código",
         [("create", "app/utilidades.py",
           '"""Utilidades de integración."""\n\n'
           '# Token ficticio creado para el experimento; no es una credencial real.\n'
           'TOKEN_API = "ghp_' + "Xk9" + 'mQ2vR7tL4wN8pZ1sB6cH3jF5dY0aE9gU2"\n')]),
    30: (DEF_SEGURIDAD, "Ruta que evalúa expresiones del usuario con eval()",
         [("append", "app/main.py",
           '\n\n@app.get("/calculadora")\ndef calculadora(expresion: str):\n'
           '    return {"resultado": eval(expresion)}\n')]),
}


def aplicar(numero: int) -> None:
    tipo, descripcion, acciones = CAMBIOS[numero]
    for accion, archivo, *args in acciones:
        ruta = RAIZ / archivo
        if accion == "append":
            texto = ruta.read_text(encoding="utf-8")
            if args[0] in texto:
                sys.exit(f"El cambio {numero} ya está aplicado en {archivo}.")
            ruta.write_text(texto + args[0], encoding="utf-8")
        elif accion == "replace":
            viejo, nuevo = args
            texto = ruta.read_text(encoding="utf-8")
            if texto.count(viejo) != 1:
                sys.exit(f"No se encontró el texto esperado en {archivo}. ¿Ya aplicaste este cambio o falta revertir otro?")
            ruta.write_text(texto.replace(viejo, nuevo), encoding="utf-8")
        elif accion == "create":
            if ruta.exists():
                sys.exit(f"El archivo {archivo} ya existe.")
            ruta.write_text(args[0], encoding="utf-8")
    print(f"Cambio {numero:02d} aplicado: {descripcion}")
    print(f'Ahora ejecuta:  git commit -am "cambio {numero:02d}: {descripcion}"')
    if any(a[0] == "create" for a in acciones):
        print("(Este cambio crea un archivo nuevo: antes del commit ejecuta  git add -A)")


def escribir_catalogo() -> None:
    destino = RAIZ / "cambios" / "catalogo.csv"
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cambio", "tipo", "descripcion"])
        for n, (tipo, desc, _) in CAMBIOS.items():
            w.writerow([n, tipo, desc])
    print(f"Catálogo escrito en {destino}")


def escribir_orden() -> None:
    orden = list(CAMBIOS)
    random.Random(SEMILLA).shuffle(orden)
    destino = RAIZ / "cambios" / "orden.csv"
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["paso", "cambio", "tipo"])
        for paso, n in enumerate(orden, 1):
            w.writerow([paso, n, CAMBIOS[n][0]])
    print(f"Orden escrito en {destino} (semilla {SEMILLA})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--catalogo":
        escribir_catalogo()
    elif arg == "--orden":
        escribir_orden()
    else:
        n = int(arg)
        if n not in CAMBIOS:
            sys.exit("El número de cambio debe estar entre 1 y 30.")
        aplicar(n)
