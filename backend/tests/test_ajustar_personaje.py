"""Pruebas del control manual del máster sobre la vida y el maná de un
personaje: curar o dañar por una cantidad cualquiera, fuera de cualquier
tirada o nodo, para corregir algo sobre la marcha o resolver un descanso
narrativo que no sea un punto_descanso formal.
"""

import uuid


def _crear_sala(client, historia_cuervo_negro, muerte_permanente=False):
    resp = client.post(
        "/salas",
        json={"master_nombre": "M", "historia_id": "cuervo_negro", "muerte_permanente": muerte_permanente},
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


def _poner_vida_mana(db, personaje_id: str, vida: int, mana: int | None = None) -> None:
    from app.models.personaje import Personaje

    p = db.get(Personaje, uuid.UUID(personaje_id))
    p.vida_actual = vida
    if mana is not None:
        p.mana_actual = mana
    db.commit()


def test_solo_el_master_puede_ajustar(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado

        ws.send_json(
            {"tipo": "ajustar_personaje", "datos": {"personaje_id": kara["personaje"]["id"], "delta_vida": 5}}
        )
        error = ws.receive_json()
        assert error["tipo"] == "error"


def test_cura_recorta_al_maximo_y_se_anuncia(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    vida_max = kara["personaje"]["vida_max"]
    _poner_vida_mana(db, kara["personaje"]["id"], vida=vida_max - 3)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "ajustar_personaje",
                "datos": {"personaje_id": kara["personaje"]["id"], "delta_vida": 999},
            }
        )
        ajuste = ws.receive_json()
        assert ajuste["tipo"] == "personaje_ajustado"
        assert ajuste["datos"]["delta_vida"] == 3  # el delta real aplicado, recortado al máximo
        assert ajuste["datos"]["delta_mana"] == 0

        actualizado = ws.receive_json()
        assert actualizado["tipo"] == "personaje_actualizado"
        assert actualizado["datos"]["vida_actual"] == vida_max  # recortado, no se pasa del máximo
        assert actualizado["datos"]["estado"] == "activo"


def test_dano_deja_inconsciente_sin_muerte_permanente(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro, muerte_permanente=False)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    _poner_vida_mana(db, kara["personaje"]["id"], vida=3)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "ajustar_personaje", "datos": {"personaje_id": kara["personaje"]["id"], "delta_vida": -10}}
        )
        ws.receive_json()  # personaje_ajustado
        actualizado = ws.receive_json()
        assert actualizado["datos"]["vida_actual"] == 0
        assert actualizado["datos"]["estado"] == "inconsciente"

        # Curarla por encima de 0 la devuelve a activo.
        ws.send_json(
            {"tipo": "ajustar_personaje", "datos": {"personaje_id": kara["personaje"]["id"], "delta_vida": 5}}
        )
        ws.receive_json()  # personaje_ajustado
        revivida = ws.receive_json()
        assert revivida["datos"]["vida_actual"] == 5
        assert revivida["datos"]["estado"] == "activo"


def test_dano_mata_con_muerte_permanente_y_resuelve_al_ultimo(client, historia_ala_norte, db):
    # cuervo_negro no define nodo_muerte_total; ala_norte sí, así que la
    # muerte permanente solo se activa de verdad con esta historia.
    resp = client.post(
        "/salas",
        json={"master_nombre": "M", "historia_id": "ala_norte", "muerte_permanente": True},
    )
    assert resp.status_code == 201, resp.text
    sala = resp.json()
    codigo = sala["sala"]["codigo"]
    thalia = _crear_personaje(client, codigo, "thalia_ticona", "Ana")
    _poner_vida_mana(db, thalia["personaje"]["id"], vida=2)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "ajustar_personaje", "datos": {"personaje_id": thalia["personaje"]["id"], "delta_vida": -5}}
        )
        ws.receive_json()  # personaje_ajustado
        actualizado = ws.receive_json()
        assert actualizado["datos"]["vida_actual"] == 0
        assert actualizado["datos"]["estado"] == "muerto"

        # Era la única con vida: la partida salta a muerte total.
        final = ws.receive_json()
        assert final["tipo"] == "nodo_actualizado"
        assert final["datos"]["finalizada"] is True
        assert final["datos"]["tipo_final"] == "muerte_total"


def test_mana_se_ajusta_de_forma_independiente_y_se_recorta(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    mana_max = kara["personaje"]["mana_max"]
    _poner_vida_mana(db, kara["personaje"]["id"], vida=kara["personaje"]["vida_actual"], mana=1)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "ajustar_personaje",
                "datos": {"personaje_id": kara["personaje"]["id"], "delta_mana": 999, "delta_vida": -1},
            }
        )
        ajuste = ws.receive_json()
        assert ajuste["datos"]["delta_mana"] == mana_max - 1
        assert ajuste["datos"]["delta_vida"] == -1

        actualizado = ws.receive_json()
        assert actualizado["datos"]["mana_actual"] == mana_max
        assert actualizado["datos"]["vida_actual"] == kara["personaje"]["vida_actual"] - 1


def test_no_se_puede_ajustar_a_un_personaje_muerto(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro, muerte_permanente=True)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    from app.models.personaje import Personaje

    p = db.get(Personaje, uuid.UUID(kara["personaje"]["id"]))
    p.estado = "muerto"
    p.vida_actual = 0
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {"tipo": "ajustar_personaje", "datos": {"personaje_id": kara["personaje"]["id"], "delta_vida": 5}}
        )
        error = ws.receive_json()
        assert error["tipo"] == "error"


def test_no_se_puede_ajustar_a_alguien_de_otra_sala(client, historia_cuervo_negro):
    sala_a = _crear_sala(client, historia_cuervo_negro)
    sala_b = _crear_sala(client, historia_cuervo_negro)
    codigo_a = sala_a["sala"]["codigo"]
    codigo_b = sala_b["sala"]["codigo"]
    de_otra_sala = _crear_personaje(client, codigo_b, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo_a}?token={sala_a['master_token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "ajustar_personaje",
                "datos": {"personaje_id": de_otra_sala["personaje"]["id"], "delta_vida": -5},
            }
        )
        error = ws.receive_json()
        assert error["tipo"] == "error"
