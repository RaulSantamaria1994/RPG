"""Endpoints de lectura de `/salas` que no tenían ninguna prueba propia:
el detalle público de la sala, la lista de pregenerados aún disponibles,
las habilidades pasivas personalizadas, el catálogo de hechizos, y el
listado de nodos (reservado al máster) que usa el selector de "forzar
salto de nodo".
"""


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_personaje(client, codigo, personaje_id="kara_la_espadachina", jugador_nombre="Ana"):
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": jugador_nombre, "personaje_pregenerado_id": personaje_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_obtener_sala_devuelve_los_datos_publicos(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    resp = client.get(f"/salas/{codigo}")
    assert resp.status_code == 200, resp.text
    datos = resp.json()
    assert datos["codigo"] == codigo
    assert datos["estado"] == "activa"
    # No se filtra el master_token ni ningún otro dato sensible.
    assert "master_token" not in datos


def test_obtener_sala_inexistente_da_404(client):
    resp = client.get("/salas/ZZZZZZ")
    assert resp.status_code == 404


def test_listar_pregenerados_excluye_los_ya_tomados(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    disponibles_antes = client.get(f"/salas/{codigo}/pregenerados").json()
    ids_antes = {p["id"] for p in disponibles_antes}
    assert "kara_la_espadachina" in ids_antes

    _crear_personaje(client, codigo, "kara_la_espadachina")

    disponibles_despues = client.get(f"/salas/{codigo}/pregenerados").json()
    ids_despues = {p["id"] for p in disponibles_despues}
    assert "kara_la_espadachina" not in ids_despues
    assert ids_despues == ids_antes - {"kara_la_espadachina"}


def test_listar_habilidades_personalizado_devuelve_las_de_la_historia(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    resp = client.get(f"/salas/{codigo}/habilidades-personalizado")
    assert resp.status_code == 200, resp.text
    ids = {h["id"] for h in resp.json()}
    assert "instinto_de_combate" in ids


def test_listar_hechizos_disponibles_combina_base_e_historia(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    resp = client.get(f"/salas/{codigo}/hechizos")
    assert resp.status_code == 200, resp.text
    ids = {h["hechizo_id"] for h in resp.json()}
    assert "grito_de_cuervo" in ids  # propio de cuervo_negro
    assert "dardo_arcano" in ids  # del catálogo base, común a toda historia


def test_listar_nodos_requiere_token_de_master(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)

    sin_token = client.get(f"/salas/{codigo}/nodos")
    assert sin_token.status_code == 401

    con_token_jugador = client.get(
        f"/salas/{codigo}/nodos", headers={"Authorization": f"Bearer {kara['token']}"}
    )
    assert con_token_jugador.status_code == 403


def test_listar_nodos_devuelve_resumen_de_todos_los_nodos(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    resp = client.get(
        f"/salas/{codigo}/nodos", headers={"Authorization": f"Bearer {sala['master_token']}"}
    )
    assert resp.status_code == 200, resp.text
    nodos = resp.json()
    ids = {n["id"] for n in nodos}
    assert "n001" in ids
    primero = next(n for n in nodos if n["id"] == "n001")
    assert set(primero.keys()) == {"id", "tipo", "texto", "es_final", "tipo_final"}
