from app.reglas import calcular_prioridad, validar_carrera


def test_salud(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_prioridad_suma_semanas_de_espera():
    assert calcular_prioridad("constancia", 14) == 5


def test_prioridad_tiene_tope():
    assert calcular_prioridad("cambio_carrera", 100) == 10


def test_carrera_no_distingue_mayusculas():
    assert validar_carrera("ia") is True
    assert validar_carrera("XX") is False


def test_crear_solicitud_devuelve_201(cliente):
    r = cliente.post("/solicitudes", json={"cuenta": "20180001", "carrera": "IA", "tipo": "constancia", "dias_espera": 7})
    assert r.status_code == 201
    assert r.json()["prioridad"] == 4


def test_dias_negativos_se_rechazan(cliente):
    r = cliente.post("/solicitudes", json={"cuenta": "20180002", "carrera": "IA", "tipo": "constancia", "dias_espera": -1})
    assert r.status_code == 422


def test_solicitud_inexistente_da_404(cliente):
    assert cliente.get("/solicitudes/999999").status_code == 404
