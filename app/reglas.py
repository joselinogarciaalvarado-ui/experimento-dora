"""Reglas de negocio. Los cambios con defecto modifican estas funciones."""
from app.catalogo import CARRERAS, TIPOS

PRIORIDAD_MAXIMA = 10


def calcular_prioridad(tipo: str, dias_espera: int) -> int:
    base = TIPOS[tipo]
    extra = 0
    return min(base + extra, PRIORIDAD_MAXIMA)


def validar_carrera(codigo: str) -> bool:
    return codigo.upper() in CARRERAS
