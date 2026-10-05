"""Pruebas de la votación en decisiones grupales sin dificultad: cada
palabra clave en modo "grupal" sin dificultad de un mismo nodo es una
opción de una única votación. Gana la más votada; un empate se rompe al
azar (reutilizando `secrets.randbelow`, igual que el resto del motor).
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


def _recibir_hasta(ws, tipo, maximo=20):
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


def test_votacion_grupal_gana_la_opcion_mas_votada(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")
    tobias = _crear_personaje(client, codigo, "tobias_el_trotamundos", "Cas")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n017"}})
        assert _recibir_hasta(ws_master, "nodo_actualizado")["datos"]["nodo_actual_id"] == "n017"

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws_kara, \
             client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws_ilyana, \
             client.websocket_connect(f"/ws/sala/{codigo}?token={tobias['token']}") as ws_tobias:
            for ws in (ws_kara, ws_ilyana, ws_tobias):
                _recibir_hasta(ws, "estado_inicial")

            ws_kara.send_json(
                {"tipo": "interactuar", "datos": {"palabra_clave": "entregarlo todo a la guardia de la ciudad"}}
            )
            voto1 = _recibir_hasta(ws_kara, "voto_registrado")
            assert voto1["datos"]["votados"] == 1
            assert voto1["datos"]["total"] == 3
            # Drenamos en los demás sockets el eco del voto de Kara antes de
            # votar con Ilyana, para no confundirlo con el suyo propio.
            _recibir_hasta(ws_ilyana, "voto_registrado")
            _recibir_hasta(ws_tobias, "voto_registrado")

            ws_ilyana.send_json(
                {"tipo": "interactuar", "datos": {"palabra_clave": "entregarlo todo a la guardia de la ciudad"}}
            )
            voto2 = _recibir_hasta(ws_ilyana, "voto_registrado")
            assert voto2["datos"]["votados"] == 2
            _recibir_hasta(ws_kara, "voto_registrado")
            _recibir_hasta(ws_tobias, "voto_registrado")

            ws_tobias.send_json(
                {"tipo": "interactuar", "datos": {"palabra_clave": "quedaros con el botín y desaparecer"}}
            )
            resultado = _recibir_hasta(ws_tobias, "votacion_resuelta")
            assert resultado["datos"]["empate"] is False
            assert resultado["datos"]["opcion_ganadora"] == "entregarlo todo a la guardia de la ciudad"
            assert resultado["datos"]["recuento"] == {
                "entregarlo todo a la guardia de la ciudad": 2,
                "quedaros con el botín y desaparecer": 1,
            }

            final = _recibir_hasta(ws_tobias, "nodo_actualizado")
            assert final["datos"]["finalizada"] is True
            assert final["datos"]["tipo_final"] == "heroico"


def test_votacion_grupal_empate_se_resuelve_al_azar(client, historia_cuervo_negro, d20_siempre_uno):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n017"}})
        assert _recibir_hasta(ws_master, "nodo_actualizado")["datos"]["nodo_actual_id"] == "n017"

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws_kara, \
             client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws_ilyana:
            _recibir_hasta(ws_kara, "estado_inicial")
            _recibir_hasta(ws_ilyana, "estado_inicial")

            ws_kara.send_json(
                {"tipo": "interactuar", "datos": {"palabra_clave": "entregarlo todo a la guardia de la ciudad"}}
            )
            _recibir_hasta(ws_kara, "voto_registrado")

            ws_ilyana.send_json(
                {"tipo": "interactuar", "datos": {"palabra_clave": "quedaros con el botín y desaparecer"}}
            )
            resultado = _recibir_hasta(ws_ilyana, "votacion_resuelta")
            assert resultado["datos"]["empate"] is True
            assert resultado["datos"]["recuento"] == {
                "entregarlo todo a la guardia de la ciudad": 1,
                "quedaros con el botín y desaparecer": 1,
            }
            # secrets.randbelow parcheado a 0 -> gana la primera en orden
            # alfabético entre las empatadas.
            assert resultado["datos"]["opcion_ganadora"] == "entregarlo todo a la guardia de la ciudad"
