"""Pruebas de la expulsión de un jugador por el máster: a diferencia de
"marcar ausente" (reversible), expulsar borra el personaje — su token deja
de servir — y corta su conexión en el acto con un código de cierre propio
(4403) para que el cliente lo distinga de un corte de red o una sesión
caducada.
"""

import pytest
from starlette.websockets import WebSocketDisconnect


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_personaje(client, codigo, personaje_id, jugador_nombre):
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": jugador_nombre, "personaje_pregenerado_id": personaje_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_solo_el_master_puede_expulsar(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado (él mismo)

        ws.send_json({"tipo": "expulsar_jugador", "datos": {"personaje_id": ilyana["personaje"]["id"]}})
        error = ws.receive_json()
        assert error["tipo"] == "error"

    resp = client.get(f"/salas/{codigo}/personajes")
    nombres = {p["nombre"] for p in resp.json()}
    assert "Ilyana la Hechicera" in nombres  # nadie fue expulsado


def test_expulsar_borra_al_personaje_y_cierra_su_conexion(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial
        ws_master.receive_json()  # jugador_conectado (él mismo)

        with client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws_expulsada:
            ws_expulsada.receive_json()  # estado_inicial
            ws_expulsada.receive_json()  # jugador_conectado (ella misma)
            assert ws_master.receive_json()["tipo"] == "jugador_conectado"

            ws_master.send_json(
                {"tipo": "expulsar_jugador", "datos": {"personaje_id": ilyana["personaje"]["id"]}}
            )

            anuncio = ws_master.receive_json()
            assert anuncio["tipo"] == "jugador_expulsado"
            assert anuncio["datos"]["personaje_id"] == ilyana["personaje"]["id"]
            assert anuncio["datos"]["nombre"] == "Ilyana la Hechicera"

            # La propia jugadora expulsada ve el aviso y luego se corta su conexión
            # con un código de cierre específico (4403), no un corte genérico.
            assert ws_expulsada.receive_json()["tipo"] == "jugador_expulsado"
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws_expulsada.receive_json()
            assert exc_info.value.code == 4403

    resp = client.get(f"/salas/{codigo}/personajes")
    nombres = {p["nombre"] for p in resp.json()}
    assert "Ilyana la Hechicera" not in nombres
    assert "Kara la Espadachina" in nombres  # el resto del grupo sigue intacto

    # El token de la jugadora expulsada ya no sirve para reconectarse.
    with client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws_reintento:
        with pytest.raises(WebSocketDisconnect):
            ws_reintento.receive_json()


def test_no_se_puede_expulsar_a_alguien_de_otra_sala(client, historia_cuervo_negro):
    sala_a = _crear_sala(client, historia_cuervo_negro)
    sala_b = _crear_sala(client, historia_cuervo_negro)
    codigo_a = sala_a["sala"]["codigo"]
    codigo_b = sala_b["sala"]["codigo"]
    de_otra_sala = _crear_personaje(client, codigo_b, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo_a}?token={sala_a['master_token']}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()

        ws_master.send_json(
            {"tipo": "expulsar_jugador", "datos": {"personaje_id": de_otra_sala["personaje"]["id"]}}
        )
        error = ws_master.receive_json()
        assert error["tipo"] == "error"

    resp = client.get(f"/salas/{codigo_b}/personajes")
    assert len(resp.json()) == 1  # sigue en su propia sala
