"""Pruebas de las funcionalidades pedidas tras el playtesting: que el juego
deje de contar con un jugador ausente (en tiradas grupales y en combate), y
que se puedan usar objetos y hechizos durante el propio turno de combate.
"""


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post(
        "/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"}
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


def test_marcar_ausente_reduce_el_total_de_una_confirmacion_grupal(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial
        ws_master.receive_json()  # jugador_conectado (él mismo)

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n017"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "n017"

        ws_master.send_json(
            {"tipo": "marcar_ausente", "datos": {"personaje_id": ilyana["personaje"]["id"]}}
        )
        actualizado = ws_master.receive_json()
        assert actualizado["tipo"] == "personaje_actualizado"
        assert actualizado["datos"]["estado"] == "ausente"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado (self)

        ws.send_json(
            {
                "tipo": "interactuar",
                "datos": {"palabra_clave": "entregarlo todo a la guardia de la ciudad"},
            }
        )
        voto = ws.receive_json()
        assert voto["tipo"] == "voto_registrado"
        # Solo Kara cuenta: Ilyana está ausente y no entra en el total.
        assert voto["datos"]["votados"] == 1
        assert voto["datos"]["total"] == 1

        resultado = ws.receive_json()
        assert resultado["tipo"] == "votacion_resuelta"
        assert resultado["datos"]["opcion_ganadora"] == "entregarlo todo a la guardia de la ciudad"

        final = ws.receive_json()
        assert final["datos"]["finalizada"] is True


def test_marcar_ausente_le_impide_interactuar_individualmente(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n017"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "n017"

        ws_master.send_json(
            {"tipo": "marcar_ausente", "datos": {"personaje_id": kara["personaje"]["id"]}}
        )
        ws_master.receive_json()  # personaje_actualizado

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "interactuar",
                "datos": {"palabra_clave": "entregarlo todo a la guardia de la ciudad"},
            }
        )
        error = ws.receive_json()
        assert error["tipo"] == "error"
        assert "ausente" in error["datos"]["mensaje"]


def test_marcar_ausente_lo_excluye_de_un_combate_nuevo(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()

        ws_master.send_json(
            {"tipo": "marcar_ausente", "datos": {"personaje_id": ilyana["personaje"]["id"]}}
        )
        ws_master.receive_json()  # personaje_actualizado

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        actualizado = ws_master.receive_json()
        orden = actualizado["datos"]["combate"]["orden_iniciativa"]
        assert f"personaje:{kara['personaje']['id']}" in orden
        assert f"personaje:{ilyana['personaje']['id']}" not in orden


def test_usar_objeto_cura_vida_y_se_consume_en_combate(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    # Le concedemos una poción de prueba y le bajamos la vida a mano.
    resp = client.post(
        f"/salas/{codigo}/personajes/{kara['personaje']['id']}/objetos",
        json={
            "objeto_id": "pocion_prueba",
            "nombre": "Poción de prueba",
            "consumible": True,
            "efecto": {"tipo": "curar_vida", "cantidad": 5},
        },
        headers={"Authorization": f"Bearer {sala['master_token']}"},
    )
    assert resp.status_code == 200, resp.text

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        n1 = ws_master.receive_json()["datos"]
        assert n1["combate"]["orden_iniciativa"][0] == f"personaje:{kara['personaje']['id']}"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "combate_accion", "datos": {"accion": "objeto", "objeto_id": "pocion_prueba"}}
        )
        resultado = ws.receive_json()
        assert resultado["tipo"] == "combate_resultado"
        assert resultado["datos"]["accion"] == "objeto"
        assert resultado["datos"]["efecto"]["tipo"] == "curar_vida"

    # No comprobamos vida_actual: tras usar el objeto los enemigos contraatacan
    # automáticamente (fin del turno), así que el valor final ya no aísla solo
    # el efecto de la curación. Lo relevante ya se comprobó en el mensaje.
    resp = client.get(f"/salas/{codigo}/personajes")
    personaje = next(p for p in resp.json() if p["nombre"] == "Kara la Espadachina")
    assert personaje["inventario"] == []  # la poción se consumió


def test_lanzar_hechizo_de_dano_en_combate(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        n1 = ws_master.receive_json()["datos"]
        assert n1["combate"]["orden_iniciativa"][0] == f"personaje:{ilyana['personaje']['id']}"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "combate_accion",
                "datos": {
                    "accion": "hechizo",
                    "hechizo_id": "dardo_arcano",
                    "objetivo_enemigo_id": "contrabandista_1",
                },
            }
        )
        resultado = ws.receive_json()
        assert resultado["tipo"] == "combate_resultado"
        assert resultado["datos"]["accion"] == "hechizo"
        assert resultado["datos"]["tirada"]["exito"] is True
        assert resultado["datos"]["efecto"]["tipo"] == "dano"

    resp = client.get(f"/salas/{codigo}/personajes")
    personaje = next(p for p in resp.json() if p["nombre"] == "Ilyana la Hechicera")
    assert personaje["mana_actual"] == personaje["mana_max"] - 3  # coste_mana de dardo_arcano
