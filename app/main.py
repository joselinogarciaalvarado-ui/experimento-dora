"""API de gestión de solicitudes estudiantiles.

Aplicación de prueba para el experimento sobre CI/CD, DevSecOps y métricas DORA.
"""
import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.catalogo import CARRERAS, TIPOS
from app.reglas import calcular_prioridad, validar_carrera

DB_PATH = os.environ.get("DB_PATH", "solicitudes.db")
VERSION = os.environ.get("APP_VERSION", "dev")
ENTORNO = os.environ.get("ENTORNO", "desarrollo")


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def iniciar_bd():
    with conectar() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS solicitudes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "cuenta TEXT NOT NULL, carrera TEXT NOT NULL, tipo TEXT NOT NULL, "
            "dias_espera INTEGER NOT NULL, prioridad INTEGER NOT NULL)"
        )


@asynccontextmanager
async def ciclo_de_vida(_app):
    iniciar_bd()
    yield


app = FastAPI(title="API de Solicitudes Estudiantiles", version=VERSION, lifespan=ciclo_de_vida)


class SolicitudEntrada(BaseModel):
    cuenta: str
    carrera: str
    tipo: str
    dias_espera: int


@app.get("/health")
def salud():
    with conectar() as con:
        con.execute("SELECT 1")
    return {"estado": "ok", "version": VERSION}


@app.post("/solicitudes", status_code=201)
def crear_solicitud(datos: SolicitudEntrada):
    if not validar_carrera(datos.carrera):
        raise HTTPException(status_code=422, detail="Carrera no válida")
    if datos.tipo not in TIPOS:
        raise HTTPException(status_code=422, detail="Tipo de solicitud no válido")
    if datos.dias_espera < 0:
        raise HTTPException(status_code=422, detail="Los días de espera no pueden ser negativos")
    prioridad = calcular_prioridad(datos.tipo, datos.dias_espera)
    with conectar() as con:
        cur = con.execute(
            "INSERT INTO solicitudes (cuenta, carrera, tipo, dias_espera, prioridad) VALUES (?, ?, ?, ?, ?)",
            (datos.cuenta, datos.carrera.upper(), datos.tipo, datos.dias_espera, prioridad),
        )
        nuevo_id = cur.lastrowid
    return {"id": nuevo_id, "prioridad": prioridad}


@app.get("/solicitudes")
def listar_solicitudes():
    with conectar() as con:
        filas = con.execute("SELECT * FROM solicitudes ORDER BY prioridad DESC, id").fetchall()
    return [dict(f) for f in filas]


@app.get("/solicitudes/{solicitud_id}")
def obtener_solicitud(solicitud_id: int):
    with conectar() as con:
        fila = con.execute("SELECT * FROM solicitudes WHERE id = ?", (solicitud_id,)).fetchone()
    if fila is None:
        return {}
    return dict(fila)


# --- Rutas agregadas por los cambios del experimento ---
