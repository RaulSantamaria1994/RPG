"""El router `/historias` no tenía ninguna prueba: listar, obtener una
concreta, validar un JSON sin persistirlo, y subir una historia nueva (o
una nueva versión de una existente).
"""

from app.models.historia import Historia

HISTORIA_MINIMA_VALIDA = {
    "historia_id": "prueba_historias_endpoint",
    "titulo": "Prueba del endpoint de historias",
    "nodo_inicial": "n1",
    "nodos": {
        "n1": {"tipo": "narrativo", "texto": "Inicio.", "es_final": True, "tipo_final": "fin"},
    },
}

HISTORIA_INVALIDA = {
    "historia_id": "prueba_historias_endpoint_invalida",
    "titulo": "Prueba inválida",
    # Sin nodo_inicial ni nodos: validar_historia debe rechazarla.
}


def test_listar_historias_incluye_las_sembradas(client, historia_cuervo_negro, historia_ala_norte):
    resp = client.get("/historias")
    assert resp.status_code == 200, resp.text
    ids = {h["historia_id"] for h in resp.json()}
    assert {"cuervo_negro", "ala_norte"} <= ids


def test_listar_historias_devuelve_solo_la_ultima_version(client, historia_cuervo_negro, db):
    resp = client.post("/historias", json={"contenido": dict(HISTORIA_MINIMA_VALIDA)})
    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 1

    resp2 = client.post("/historias", json={"contenido": dict(HISTORIA_MINIMA_VALIDA)})
    assert resp2.status_code == 201, resp2.text
    assert resp2.json()["version"] == 2

    listado = client.get("/historias").json()
    entradas = [h for h in listado if h["historia_id"] == "prueba_historias_endpoint"]
    assert len(entradas) == 1
    assert entradas[0]["version"] == 2


def test_obtener_historia_devuelve_la_ultima_version_con_contenido(client, historia_cuervo_negro):
    resp = client.get("/historias/cuervo_negro")
    assert resp.status_code == 200, resp.text
    datos = resp.json()
    assert datos["historia_id"] == "cuervo_negro"
    assert "nodos" in datos["contenido"]


def test_obtener_historia_inexistente_da_404(client):
    resp = client.get("/historias/esto-no-existe")
    assert resp.status_code == 404


def test_validar_contenido_valido_no_persiste_nada(client, db):
    antes = db.query(Historia).count()

    resp = client.post("/historias/validar", json={"contenido": dict(HISTORIA_MINIMA_VALIDA)})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"valida": True, "errores": []}

    assert db.query(Historia).count() == antes


def test_validar_contenido_invalido_devuelve_errores_sin_persistir(client, db):
    antes = db.query(Historia).count()

    resp = client.post("/historias/validar", json={"contenido": dict(HISTORIA_INVALIDA)})
    assert resp.status_code == 200, resp.text
    datos = resp.json()
    assert datos["valida"] is False
    assert len(datos["errores"]) > 0

    assert db.query(Historia).count() == antes


def test_crear_historia_valida_queda_marcada_como_validada(client):
    resp = client.post("/historias", json={"contenido": dict(HISTORIA_MINIMA_VALIDA)})
    assert resp.status_code == 201, resp.text
    datos = resp.json()
    assert datos["validada"] is True
    assert datos["errores_validacion"] is None
    assert datos["version"] == 1


def test_crear_historia_invalida_se_persiste_sin_validar(client):
    """Subir contenido inválido no se rechaza con un error HTTP: se guarda
    igualmente, marcado como `validada: False` con sus errores, para que se
    pueda revisar y corregir después. `POST /salas` sí la rechazará mientras
    siga así, al filtrar por `validada=True`."""
    resp = client.post("/historias", json={"contenido": dict(HISTORIA_INVALIDA)})
    assert resp.status_code == 201, resp.text
    datos = resp.json()
    assert datos["validada"] is False
    assert len(datos["errores_validacion"]) > 0

    resp_sala = client.post(
        "/salas",
        json={
            "master_nombre": "M",
            "historia_id": "prueba_historias_endpoint_invalida",
        },
    )
    assert resp_sala.status_code == 404


def test_crear_historia_sin_historia_id_da_422(client):
    resp = client.post("/historias", json={"contenido": {"titulo": "Sin id"}})
    assert resp.status_code == 422
