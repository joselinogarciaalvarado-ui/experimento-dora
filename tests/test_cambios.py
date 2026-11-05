"""Pruebas agregadas por los cambios normales del experimento."""
from app.catalogo import CARRERAS, TIPOS  # noqa: F401


def test_tipo_titulo():
    from app.reglas import calcular_prioridad
    assert calcular_prioridad("titulo", 0) == 8


def test_tipo_reposicion_examen():
    from app.reglas import calcular_prioridad
    assert calcular_prioridad("reposicion_examen", 0) == 6


def test_carrera_ci():
    assert CARRERAS["CI"] == "Comercio Internacional"


def test_carrera_ae():
    assert CARRERAS["AE"] == "Administración de Empresas"


def test_carrera_mk():
    assert CARRERAS["MK"] == "Mercadotecnia"


def test_carrera_ec():
    assert CARRERAS["EC"] == "Economía"


def test_tipo_beca():
    from app.reglas import calcular_prioridad
    assert calcular_prioridad("beca", 0) == 7


def test_carrera_ic():
    assert CARRERAS["IC"] == "Ingeniería Civil"


def test_tipo_equivalencias():
    from app.reglas import calcular_prioridad
    assert calcular_prioridad("equivalencias", 0) == 4
