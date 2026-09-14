"""Pruebas de la historia tributo (El ala norte): que la seed sea válida y
que se pueda crear cada uno de los personajes pregenerados con los atributos
y la vida que se definieron para ellos.
"""


def _crear_sala(client):
    resp = client.post(
        "/salas", json={"master_nombre": "El Máster", "historia_id": "ala_norte"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_historia_ala_norte_es_valida(contenido_ala_norte):
    from app.engine.validator import validar_historia

    resultado = validar_historia(contenido_ala_norte)
    assert resultado.valida
    assert resultado.errores == []


def test_crear_sala_ala_norte(client, historia_ala_norte):
    datos = _crear_sala(client)
    assert datos["sala"]["historia_version"] == 1
    assert datos["sala"]["codigo"]


PERSONAJES_ESPERADOS = {
    "thalia_ticona": {
        "nombre": "Dra. Thalia Ticona",
        "atributos": {"fuerza": 1, "astucia": 3, "voluntad": 5, "agilidad": 3},
        "vida_max": 16,
        "habilidad_pasiva": "instinto_de_uci",
    },
    "hugo_bravo": {
        "nombre": "Hugo Bravo",
        "atributos": {"fuerza": 5, "astucia": 2, "voluntad": 2, "agilidad": 3},
        "vida_max": 24,
        "habilidad_pasiva": "reflejos_de_rescate",
    },
    "marina_solis": {
        "nombre": "Marina Solís",
        "atributos": {"fuerza": 1, "astucia": 5, "voluntad": 2, "agilidad": 4},
        "vida_max": 16,
        "habilidad_pasiva": "ojo_de_periodista",
    },
    "elena_duarte": {
        "nombre": "Elena Duarte",
        "atributos": {"fuerza": 2, "astucia": 2, "voluntad": 5, "agilidad": 3},
        "vida_max": 18,
        "habilidad_pasiva": "templanza",
    },
    "noa_ferreira": {
        "nombre": "Noa Ferreira",
        "atributos": {"fuerza": 2, "astucia": 3, "voluntad": 2, "agilidad": 5},
        "vida_max": 18,
        "habilidad_pasiva": "paso_ligero",
    },
}


def test_todos_los_pregenerados_de_ala_norte_suman_12_puntos():
    # Mismo total de puntos que reparte construir_personalizado, para que el
    # grupo quede equilibrado entre sí aunque el motor no lo obligue para
    # personajes pregenerados.
    for datos in PERSONAJES_ESPERADOS.values():
        assert sum(datos["atributos"].values()) == 12


def test_crear_cada_personaje_pregenerado_de_ala_norte(client, historia_ala_norte):
    sala = _crear_sala(client)
    codigo = sala["sala"]["codigo"]

    for i, (personaje_id, esperado) in enumerate(PERSONAJES_ESPERADOS.items()):
        resp = client.post(
            f"/salas/{codigo}/personajes/pregenerado",
            json={"jugador_nombre": f"Jugador {i}", "personaje_pregenerado_id": personaje_id},
        )
        assert resp.status_code == 201, resp.text
        p = resp.json()["personaje"]
        assert p["nombre"] == esperado["nombre"]
        assert p["fuerza"] == esperado["atributos"]["fuerza"]
        assert p["astucia"] == esperado["atributos"]["astucia"]
        assert p["voluntad"] == esperado["atributos"]["voluntad"]
        assert p["agilidad"] == esperado["atributos"]["agilidad"]
        assert p["vida_max"] == esperado["vida_max"]
        assert p["vida_actual"] == esperado["vida_max"]
        assert p["habilidad_pasiva"] == esperado["habilidad_pasiva"]
        assert p["origen"] == "pregenerado"


def test_habilidades_pasivas_de_ala_norte_cubren_las_de_los_pregenerados(contenido_ala_norte):
    ids_catalogo = {h["id"] for h in contenido_ala_norte["habilidades_pasivas_personalizado"]}
    ids_usadas = {p["habilidad_pasiva"] for p in contenido_ala_norte["personajes_pregenerados"]}
    assert ids_usadas <= ids_catalogo


def test_flujo_real_hasta_una_palabra_clave_sin_dificultad_de_ala_norte(
    client, historia_ala_norte
):
    """Smoke test de extremo a extremo sobre la propia seed: n001 -> n001b ->
    n002 -> nB1 (fallo) -> cB1 (victoria) -> nB2 -> nBr -> nBc, y en nBc se
    resuelve la palabra clave grupal sin tirada que otorga `prueba` — el
    mismo tipo de nodo que tuvimos que arreglar durante la conversión.
    """
    sala = _crear_sala(client)
    codigo = sala["sala"]["codigo"]
    creado = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": "Jugador 1", "personaje_pregenerado_id": "thalia_ticona"},
    ).json()
    token = creado["token"]

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial
        ws_master.receive_json()  # jugador_conectado (él mismo)

        with client.websocket_connect(f"/ws/sala/{codigo}?token={token}") as ws:
            ws.receive_json()  # estado_inicial
            ws.receive_json()  # jugador_conectado (self)
            ws_master.receive_json()  # jugador_conectado (Thalia, visto por el máster)

            ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "nBc"}})
            assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "nBc"
            assert ws.receive_json()["datos"]["nodo_actual_id"] == "nBc"

            ws.send_json({"tipo": "interactuar", "datos": {"palabra_clave": "guardar la carpeta"}})
            assert ws.receive_json()["tipo"] == "confirmacion_registrada"

            resultado = ws.receive_json()
            assert resultado["tipo"] == "tirada_resultado"
            assert resultado["datos"]["exito"] is True
            assert resultado["datos"]["tirada"]["sin_tirada"] is True

            actualizado = ws.receive_json()
            assert actualizado["tipo"] == "nodo_actualizado"
            assert actualizado["datos"]["nodo_actual_id"] == "nBs2"
            assert any(
                o.get("objeto_id") == "prueba" for o in actualizado["datos"]["inventario_grupo"]
            )
