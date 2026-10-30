"""Pruebas de integración del flujo central del spec: crear sala, unirse,
interactuar con una palabra clave -> tirada -> nodo destino, encadenar
nodos narrativos, lanzar un hechizo (con coste de maná) y disparar un
combate por rondas, todo pasando por la API REST + el WebSocket real.
"""


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post(
        "/salas",
        json={"master_nombre": "El Máster", "historia_id": "cuervo_negro"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_personaje_pregenerado(client, codigo, personaje_id, jugador_nombre="Jugador 1"):
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": jugador_nombre, "personaje_pregenerado_id": personaje_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _recibir_hasta(ws, tipo, maximo=10):
    """Lee mensajes de `ws` saltándose los que no sean `tipo`. Con dos
    conexiones abiertas a la vez (p. ej. jugador + máster), el orden exacto
    en que cada una ve el 'jugador_conectado' de la otra no está
    garantizado con el TestClient síncrono — así que no se asume posición,
    solo se busca el mensaje que de verdad importa para la prueba."""
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


def test_crear_sala_ancla_version_y_nodo_inicial(client, historia_cuervo_negro):
    datos = _crear_sala(client, historia_cuervo_negro)
    assert len(datos["sala"]["codigo"]) == 6
    assert datos["sala"]["historia_version"] == 1
    assert datos["sala"]["min_jugadores"] == 1
    assert datos["sala"]["max_jugadores"] == 6


def test_crear_personaje_pregenerado_copia_atributos_de_la_historia(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    creado = _crear_personaje_pregenerado(client, sala["sala"]["codigo"], "kara_la_espadachina")
    p = creado["personaje"]
    assert p["nombre"] == "Kara la Espadachina"
    assert p["fuerza"] == 5 and p["astucia"] == 2 and p["voluntad"] == 2 and p["agilidad"] == 4
    assert p["vida_max"] == 24
    assert creado["token"]


def test_no_se_puede_repetir_personaje_pregenerado_en_la_misma_sala(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    _crear_personaje_pregenerado(client, codigo, "kara_la_espadachina", "Jugador 1")
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": "Jugador 2", "personaje_pregenerado_id": "kara_la_espadachina"},
    )
    assert resp.status_code == 409


def test_flujo_nodo_tirada_nodo_via_atributo(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    creado = _crear_personaje_pregenerado(client, codigo, "kara_la_espadachina")
    token = creado["token"]

    with client.websocket_connect(f"/ws/sala/{codigo}?token={token}") as ws, \
            client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        inicial = _recibir_hasta(ws, "estado_inicial")
        assert inicial["datos"]["nodo_actual_id"] == "n001"

        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "hombre apoyado en la pared"}}
        )
        _recibir_hasta(ws, "palabra_clave_bloqueada")

        resultado = _recibir_hasta(ws, "tirada_resultado")
        assert resultado["datos"]["exito"] is True
        assert resultado["datos"]["tirada"]["total"] == 22  # d20(20) + astucia(2)

        actualizado = _recibir_hasta(ws, "nodo_actualizado")
        assert actualizado["datos"]["nodo_actual_id"] == "n002"

        _recibir_hasta(ws, "palabra_clave_liberada")

        # Avanzar un nodo narrativo es cosa del máster, no del jugador.
        ws_master.send_json({"tipo": "continuar", "datos": {}})
        assert _recibir_hasta(ws, "nodo_actualizado")["datos"]["nodo_actual_id"] == "n004"

        ws_master.send_json({"tipo": "continuar", "datos": {}})
        siguiente = _recibir_hasta(ws, "nodo_actualizado")
        assert siguiente["datos"]["nodo_actual_id"] == "n006"
        assert siguiente["datos"]["nodo"]["tipo"] == "interactivo"


def test_jugador_no_puede_avanzar_un_nodo_narrativo(client, historia_cuervo_negro):
    """Avanzar un nodo narrativo ("continuar") es una decisión del máster,
    no del jugador — este botón ya no existe en la pantalla del jugador,
    pero el backend lo rechaza igualmente si llega por ahí."""
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    creado = _crear_personaje_pregenerado(client, codigo, "kara_la_espadachina")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={creado['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado

        ws.send_json({"tipo": "continuar", "datos": {}})
        error = ws.receive_json()
        assert error["tipo"] == "error"
        assert "máster" in error["datos"]["mensaje"]


def test_palabra_clave_individual_sin_dificultad_no_tira_dado(
    client, historia_cuervo_negro
):
    """'preguntar al tabernero por rumores' es individual y no tiene
    atributo/dificultad: debe resolverse como éxito automático, igual que ya
    pasa con las palabras clave grupales sin dificultad."""
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    creado = _crear_personaje_pregenerado(client, codigo, "kara_la_espadachina")
    token = creado["token"]

    with client.websocket_connect(f"/ws/sala/{codigo}?token={token}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado

        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "preguntar al tabernero por rumores"}}
        )
        assert ws.receive_json()["tipo"] == "palabra_clave_bloqueada"

        resultado = ws.receive_json()
        assert resultado["tipo"] == "tirada_resultado"
        assert resultado["datos"]["exito"] is True
        assert resultado["datos"]["tirada"] == {"exito": True, "sin_tirada": True}

        actualizado = ws.receive_json()
        assert actualizado["tipo"] == "nodo_actualizado"
        assert actualizado["datos"]["nodo_actual_id"] == "n001_info"


def test_flujo_fallo_lleva_a_nodo_de_fallo_y_agota_palabra_clave(
    client, historia_cuervo_negro, d20_siempre_uno
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    creado = _crear_personaje_pregenerado(client, codigo, "kara_la_espadachina")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={creado['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado

        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "hombre apoyado en la pared"}}
        )
        ws.receive_json()  # bloqueada
        resultado = ws.receive_json()
        assert resultado["datos"]["exito"] is False
        actualizado = ws.receive_json()
        assert actualizado["datos"]["nodo_actual_id"] == "n003"
        assert "n001:hombre apoyado en la pared" in actualizado["datos"]["palabras_clave_usadas"]
        ws.receive_json()  # liberada

        # La palabra clave ya está agotada: reintentar debe fallar con un error,
        # no con una nueva tirada (las decisiones pesan).
        ws.send_json(
            {
                "tipo": "interactuar",
                "datos": {"palabra_clave": "perseguirlo"},
            }
        )
        # (estamos en n003 ahora; "perseguirlo" sí está disponible aquí)
        ws.receive_json()  # bloqueada
        resultado2 = ws.receive_json()
        assert resultado2["datos"]["exito"] is False  # d20=1 -> falla también
        final = ws.receive_json()
        assert final["datos"]["nodo_actual_id"] == "n005"
        assert final["datos"]["flags"].get("pista_perdida") is True
        ws.receive_json()  # liberada


def test_lanzar_hechizo_consume_mana_y_usa_dificultad_del_hechizo(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    master_token = sala["master_token"]
    creado = _crear_personaje_pregenerado(client, codigo, "ilyana_la_hechicera")

    # El máster fuerza el salto de nodo y se desconecta; el estado queda
    # persistido en PostgreSQL (no en memoria), así que el jugador lo verá
    # aunque se conecte después y el máster ya no esté conectado — el mismo
    # mecanismo que sostiene la reconexión del spec.
    with client.websocket_connect(f"/ws/sala/{codigo}?token={master_token}") as ws_master:
        ws_master.receive_json()  # estado_inicial del máster
        ws_master.receive_json()  # jugador_conectado (él mismo)

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n006"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "n006"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={creado['token']}") as ws:
        inicial = ws.receive_json()
        assert inicial["datos"]["nodo_actual_id"] == "n006"
        ws.receive_json()  # jugador_conectado (self)

        ws.send_json(
            {
                "tipo": "interactuar",
                "datos": {
                    "palabra_clave": "forzar la puerta lateral",
                    "via": "hechizo",
                    "hechizo_id": "luz_fantasma",
                },
            }
        )
        ws.receive_json()  # bloqueada

        resultado = ws.receive_json()
        assert resultado["datos"]["tirada"]["hechizo"] == "Luz fantasma"
        assert resultado["datos"]["exito"] is True

        actualizado = ws.receive_json()
        assert actualizado["datos"]["nodo_actual_id"] == "n007"

        ws.receive_json()  # liberada

    resp = client.get(f"/salas/{codigo}/estado", headers={"Authorization": f"Bearer {master_token}"})
    personajes = resp.json()["personajes"]
    ilyana = next(p for p in personajes if p["nombre"] == "Ilyana la Hechicera")
    assert ilyana["mana_actual"] == 14  # 16 - coste_mana(2) de luz_fantasma


def test_combate_por_rondas_aplica_dano_y_avanza_turnos(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    master_token = sala["master_token"]
    creado = _crear_personaje_pregenerado(client, codigo, "kara_la_espadachina")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={master_token}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        n1 = ws_master.receive_json()["datos"]
        assert n1["fase"] == "combate"
        assert n1["combate"]["orden_iniciativa"][0] == f"personaje:{creado['personaje']['id']}"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={creado['token']}") as ws:
        inicial = ws.receive_json()["datos"]
        assert inicial["fase"] == "combate"
        ws.receive_json()  # jugador_conectado (self)

        ws.send_json(
            {"tipo": "combate_accion", "datos": {"accion": "atacar", "enemigo_id": "contrabandista_1"}}
        )

        primer_resultado = ws.receive_json()
        assert primer_resultado["tipo"] == "combate_resultado"
        assert primer_resultado["datos"]["origen"] == "jugador"
        assert primer_resultado["datos"]["dano_aplicado"] == 4  # fuerza(5)//2 + 2

        # El combate es reactivo: el enemigo atacado responde de inmediato,
        # sin esperar un turno propio (el otro enemigo, al que nadie ha
        # atacado, no hace nada).
        reaccion = ws.receive_json()
        assert reaccion["tipo"] == "combate_resultado"
        assert reaccion["datos"]["origen"] == "enemigo"

        actualizado = ws.receive_json()
        assert actualizado["tipo"] == "personaje_actualizado"

        siguiente = ws.receive_json()
        assert siguiente["tipo"] == "nodo_actualizado"

    resp = client.get(f"/salas/{codigo}/estado", headers={"Authorization": f"Bearer {master_token}"})
    estado = resp.json()["estado"]
    assert estado["combate"]["enemigos"][0]["vida"] == 6  # 10 - 4 de daño
    assert estado["combate"]["turno_index"] == 0  # ha vuelto a ser el turno de Kara
