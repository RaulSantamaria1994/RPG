"""Pruebas de la muerte permanente: cuando muerte_permanente está activo en
la sala y la historia define 'nodo_muerte_total' (solo "El ala norte" por
ahora), llegar a 0 de vida mata al personaje. Si no es el último con vida,
solo él recibe un desenlace tétrico personal y el resto del grupo sigue
jugando; si es el último, toda la partida salta al epílogo de muerte total.
"""

import uuid


def _crear_sala(client, muerte_permanente=True):
    resp = client.post(
        "/salas",
        json={
            "master_nombre": "M",
            "historia_id": "ala_norte",
            "muerte_permanente": muerte_permanente,
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


def _poner_vida(db, personaje_id: str, vida: int) -> None:
    from app.models.personaje import Personaje

    p = db.get(Personaje, uuid.UUID(personaje_id))
    p.vida_actual = vida
    db.commit()


def test_muerte_no_es_la_ultima_da_epilogo_personal_y_el_grupo_sigue(
    client, historia_ala_norte, db, d20_siempre_uno
):
    sala = _crear_sala(client, muerte_permanente=True)
    codigo = sala["sala"]["codigo"]
    thalia = _crear_personaje(client, codigo, "thalia_ticona", "Ana")
    hugo = _crear_personaje(client, codigo, "hugo_bravo", "Bob")

    _poner_vida(db, thalia["personaje"]["id"], 3)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial
        ws_master.receive_json()  # jugador_conectado (él mismo)
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "nD1"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "nD1"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={thalia['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "avanzar con cuidado"}}
        )

        assert ws.receive_json()["tipo"] == "palabra_clave_bloqueada"

        tirada = ws.receive_json()
        assert tirada["tipo"] == "tirada_resultado"
        assert tirada["datos"]["exito"] is False

        actualizado = ws.receive_json()
        assert actualizado["tipo"] == "personaje_actualizado"
        assert actualizado["datos"]["estado"] == "muerto"
        assert actualizado["datos"]["vida_actual"] == 0

        muerte = ws.receive_json()
        assert muerte["tipo"] == "personaje_muerto"
        assert muerte["datos"]["personaje_id"] == thalia["personaje"]["id"]
        assert len(muerte["datos"]["epilogo"]) > 0

        # El grupo sigue: se avanza al nodo de fallo normal (nD2),
        # la partida global NO termina.
        siguiente = ws.receive_json()
        assert siguiente["tipo"] == "nodo_actualizado"
        assert siguiente["datos"]["finalizada"] is False

        assert ws.receive_json()["tipo"] == "palabra_clave_liberada"

    resp = client.get(f"/salas/{codigo}/personajes")
    personajes = {p["nombre"]: p for p in resp.json()}
    assert personajes["Dra. Thalia Ticona"]["estado"] == "muerto"
    assert personajes["Hugo Bravo"]["estado"] == "activo"


def test_muerte_del_ultimo_personaje_termina_la_partida_en_muerte_total(
    client, historia_ala_norte, db, d20_siempre_uno
):
    sala = _crear_sala(client, muerte_permanente=True)
    codigo = sala["sala"]["codigo"]
    thalia = _crear_personaje(client, codigo, "thalia_ticona", "Ana")

    _poner_vida(db, thalia["personaje"]["id"], 3)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "nD1"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "nD1"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={thalia['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "avanzar con cuidado"}}
        )

        assert ws.receive_json()["tipo"] == "palabra_clave_bloqueada"

        tirada = ws.receive_json()
        assert tirada["datos"]["exito"] is False

        actualizado = ws.receive_json()
        assert actualizado["datos"]["estado"] == "muerto"

        final = ws.receive_json()
        assert final["tipo"] == "nodo_actualizado"
        assert final["datos"]["nodo_actual_id"] == "n_muerte_total"
        assert final["datos"]["finalizada"] is True
        assert final["datos"]["tipo_final"] == "muerte_total"

        assert ws.receive_json()["tipo"] == "palabra_clave_liberada"


def test_sin_muerte_permanente_0_de_vida_deja_inconsciente_no_muerto(
    client, historia_ala_norte, db, d20_siempre_uno
):
    sala = _crear_sala(client, muerte_permanente=False)
    codigo = sala["sala"]["codigo"]
    thalia = _crear_personaje(client, codigo, "thalia_ticona", "Ana")

    _poner_vida(db, thalia["personaje"]["id"], 3)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "nD1"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "nD1"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={thalia['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "interactuar", "datos": {"palabra_clave": "avanzar con cuidado"}}
        )

        assert ws.receive_json()["tipo"] == "palabra_clave_bloqueada"

        tirada = ws.receive_json()
        assert tirada["datos"]["exito"] is False

        actualizado = ws.receive_json()
        assert actualizado["tipo"] == "personaje_actualizado"
        assert actualizado["datos"]["estado"] == "inconsciente"

        siguiente = ws.receive_json()
        assert siguiente["tipo"] == "nodo_actualizado"
        assert siguiente["datos"]["nodo_actual_id"] == "nD2"
        assert siguiente["datos"]["finalizada"] is False


def test_un_personaje_muerto_no_cuenta_para_confirmaciones_grupales(
    client, historia_ala_norte, db, d20_siempre_veinte
):
    sala = _crear_sala(client, muerte_permanente=True)
    codigo = sala["sala"]["codigo"]
    thalia = _crear_personaje(client, codigo, "thalia_ticona", "Ana")
    hugo = _crear_personaje(client, codigo, "hugo_bravo", "Bob")

    from app.models.personaje import Personaje

    p = db.get(Personaje, uuid.UUID(thalia["personaje"]["id"]))
    p.estado = "muerto"
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n002"}})
        assert ws_master.receive_json()["datos"]["nodo_actual_id"] == "n002"

    with client.websocket_connect(f"/ws/sala/{codigo}?token={hugo['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "interactuar",
                "datos": {"palabra_clave": "Entrar ya en el box 4"},
            }
        )
        voto = ws.receive_json()
        assert voto["tipo"] == "voto_registrado"
        # Solo Hugo cuenta: Thalia ha muerto y no entra en el total.
        assert voto["datos"]["votados"] == 1
        assert voto["datos"]["total"] == 1
