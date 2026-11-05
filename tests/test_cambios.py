"""Pruebas agregadas por los cambios normales del experimento."""
from app.catalogo import CARRERAS, TIPOS  # noqa: F401


def test_tipo_titulo():
    from app.reglas import calcular_prioridad
    assert calcular_prioridad("titulo", 0) == 8


def test_tipo_reposicion_examen():
    from app.reglas import calcular_prioridad
    assert calcular_prioridad("reposicion_examen", 0) == 6
