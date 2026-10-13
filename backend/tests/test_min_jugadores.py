"""`min_jugadores` se guardaba al crear la sala pero nada lo hacía
cumplir: con el valor por defecto en 1 nadie lo notaba. Esto prueba el
enforcement real: mientras no se haya unido suficiente gente, ni
`interactuar` ni `continuar` dejan avanzar la historia (lo pida el
jugador o el propio máster) — pero las herramientas de override del
máster siguen funcionando, porque son precisamente la vía para saltarse
las reglas normales a propósito.
"""


def _crear_sala(client, historia_cuervo_negro, min_jugadores):
    resp = client.post(
        "/salas",
        json={
            "master_nombre": "M",
            "historia_id": "cuervo_negro",
            "min_jugadores": min_jugadores,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_personaje(client, codigo, personaje_id, jugador_nombre):
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": jugador_nombre, "personaje_pregenerado_id": personaje_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _recibir_hasta(ws, tipo, maximo=20):
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


def test_interactuar_bloqueado_por_debajo_del_minimo(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro, min_jugadores=2)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "preguntar al tabernero por rumores"}}
        )
        error = _recibir_hasta(ws, "error")
        assert "al menos 2 jugadores" in error["datos"]["mensaje"]
        assert "falta 1" in error["datos"]["mensaje"]


def test_interactuar_se_permite_al_alcanzar_el_minimo(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro, min_jugadores=2)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "preguntar al tabernero por rumores"}}
        )
        resultado = _recibir_hasta(ws, "tirada_resultado")
        assert resultado["datos"]["exito"] is True


def test_continuar_bloqueado_por_debajo_del_minimo_incluso_para_el_master(
    client, historia_cuervo_negro
):
    sala = _crear_sala(client, historia_cuervo_negro, min_jugadores=2)
    codigo = sala["sala"]["codigo"]
    _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n001_info"}})
        _recibir_hasta(ws_master, "nodo_actualizado")

        # Ni el propio máster puede saltarse el mínimo con su botón normal
        # de "continuar" — solo con un override explícito.
        ws_master.send_json({"tipo": "continuar", "datos": {}})
        error = _recibir_hasta(ws_master, "error")
        assert "al menos 2 jugadores" in error["datos"]["mensaje"]


def test_override_nodo_y_override_resultado_no_se_bloquean_por_el_minimo(
    client, historia_cuervo_negro
):
    """Los overrides del máster son precisamente la vía para saltarse las
    reglas normales a propósito — no tendría sentido que el propio mínimo
    de jugadores se lo impidiera."""
    sala = _crear_sala(client, historia_cuervo_negro, min_jugadores=2)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n009"}})
        actualizado = _recibir_hasta(ws_master, "nodo_actualizado")
        assert actualizado["datos"]["nodo_actual_id"] == "n009"

        ws_master.send_json(
            {
                "tipo": "override_resultado",
                "datos": {
                    "personaje_id": kara["personaje"]["id"],
                    "palabra_clave": "escuchar las voces al fondo",
                    "exito": True,
                },
            }
        )
        # No debe llegar ningún error por el mínimo de jugadores (si lo
        # bloqueara, lo siguiente sería un 'error', no un 'tirada_resultado').
        resultado = _recibir_hasta(ws_master, "tirada_resultado")
        assert resultado["datos"]["palabra_clave"] == "escuchar las voces al fondo"


def test_el_minimo_por_defecto_es_uno_y_no_bloquea_nada(client, historia_cuervo_negro):
    """Hoy nadie puede elegir min_jugadores desde la app (no hay control en
    la pantalla de crear sala), así que el valor por defecto debe seguir
    permitiendo jugar en solitario como siempre — el enforcement solo debe
    notarse quien pida explícitamente un mínimo más alto."""
    sala = client.post(
        "/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"}
    ).json()
    assert sala["sala"]["min_jugadores"] == 1
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "preguntar al tabernero por rumores"}}
        )
        resultado = _recibir_hasta(ws, "tirada_resultado")
        assert resultado["datos"]["exito"] is True
