"""Pruebas del combate reactivo: los enemigos ya no tienen turno propio en
`orden_iniciativa` (solo los jugadores lo tienen) y responden de inmediato
a la acción del jugador que los implica, sin esperar a nada. Un enemigo al
que nadie ataca no hace nada.

Dos de estas pruebas (reacción de un enemigo concreto, aturdir por
hechizo) corresponden al modelo de combate viejo (un paso de "reacción"
aparte tras cada acción) que el motor PbtA sustituye por el contraataque
dentro de la propia banda de la movida — quedan `skip` hasta la Fase 3.
"""

import uuid

import pytest


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


def test_orden_iniciativa_solo_tiene_personajes(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        n1 = ws_master.receive_json()["datos"]

    orden = n1["combate"]["orden_iniciativa"]
    assert len(orden) == 2
    assert set(orden) == {
        f"personaje:{kara['personaje']['id']}",
        f"personaje:{ilyana['personaje']['id']}",
    }
    assert not any(e.startswith("enemigo:") for e in orden)


@pytest.mark.skip(reason="modelo de reacción del combate viejo — rehacer en la Fase 3")
def test_solo_responde_el_enemigo_atacado_el_otro_no_hace_nada(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        n1 = ws_master.receive_json()["datos"]

    primer_turno = n1["combate"]["orden_iniciativa"][0]
    atacante_id = primer_turno.split(":", 1)[1]
    atacante = kara if atacante_id == kara["personaje"]["id"] else ilyana

    with client.websocket_connect(f"/ws/sala/{codigo}?token={atacante['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado (self)

        ws.send_json(
            {"tipo": "combate_accion", "datos": {"accion": "atacar", "enemigo_id": "contrabandista_1"}}
        )

        ataque = ws.receive_json()
        assert ataque["tipo"] == "combate_resultado"
        assert ataque["datos"]["origen"] == "jugador"
        assert ataque["datos"]["enemigo_id"] == "contrabandista_1"

        reaccion = ws.receive_json()
        assert reaccion["tipo"] == "combate_resultado"
        assert reaccion["datos"]["origen"] == "enemigo"

        actualizado = ws.receive_json()
        assert actualizado["tipo"] == "personaje_actualizado"
        assert actualizado["datos"]["id"] == atacante["personaje"]["id"]

        siguiente = ws.receive_json()
        assert siguiente["tipo"] == "nodo_actualizado"
        # Le toca al otro jugador: el enemigo no ha consumido ningún "turno".
        assert siguiente["datos"]["combate"]["orden_iniciativa"][
            siguiente["datos"]["combate"]["turno_index"]
        ] != primer_turno

    resp = client.get(f"/salas/{codigo}/estado", headers={"Authorization": f"Bearer {sala['master_token']}"})
    enemigos = {e["enemigo_id"]: e for e in resp.json()["estado"]["combate"]["enemigos"]}
    assert enemigos["contrabandista_1"]["vida"] == 6  # 10 - 4 de daño
    assert enemigos["contrabandista_2"]["vida"] == 10  # nadie lo ha atacado: no actúa


@pytest.mark.skip(reason="modelo de reacción del combate viejo — rehacer en la Fase 3")
def test_hechizo_aturdir_evita_que_ese_enemigo_responda(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        ws_master.receive_json()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws:
        ws.receive_json()
        ws.receive_json()

        ws.send_json(
            {
                "tipo": "combate_accion",
                "datos": {
                    "accion": "hechizo",
                    "hechizo_id": "grito_de_cuervo",
                    "objetivo_enemigo_id": "contrabandista_1",
                },
            }
        )

        resultado = ws.receive_json()
        assert resultado["tipo"] == "combate_resultado"
        assert resultado["datos"]["efecto"]["tipo"] == "aturdido"

        # Un aturdimiento recién aplicado no se "consume" en el mismo
        # instante: el enemigo, aturdido, no responde esta vez.
        siguiente = ws.receive_json()
        assert siguiente["tipo"] == "nodo_actualizado"

    resp = client.get(f"/salas/{codigo}/personajes")
    personaje = next(p for p in resp.json() if p["nombre"] == "Ilyana la Hechicera")
    assert personaje["vida_actual"] == personaje["vida_max"]  # no ha recibido ningún golpe
