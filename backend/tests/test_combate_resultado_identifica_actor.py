"""`combate_resultado` para una acción de jugador (atacar, huir, negociar,
objeto, hechizo) debe decir quién actuó: sin `personaje_id`/`personaje_nombre`
en el mensaje, cualquier cliente que no sea el propio actor no tiene forma
de saber de quién fue la acción — y el store del frontend, al no tener ese
dato, terminaba atribuyéndosela por defecto al propio personaje de quien
mira la pantalla (el bug real que motivó esto: el registro de actividad de
un jugador mostraba su propio nombre en acciones de combate de OTRO
jugador).

Las de atacar/huir/negociar/hechizo usan el vocabulario de acciones viejo
(ahora es golpear/proteger/escabullirse/actuar_bajo_presion, sin negociar
ni hechizo en combate — ver docs/motor_pbta_plan.md) — quedan `skip` hasta
la Fase 3. La de "usar_objeto" no cambia y se queda tal cual.
"""

import pytest


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


def _entrar_en_combate(client, codigo, master_token):
    with client.websocket_connect(f"/ws/sala/{codigo}?token={master_token}") as ws_master:
        ws_master.receive_json()
        ws_master.receive_json()
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        ws_master.receive_json()


@pytest.mark.skip(reason="vocabulario de acciones de combate retirado — rehacer en la Fase 3")
def test_atacar_identifica_al_personaje_que_ataca(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    _entrar_en_combate(client, codigo, sala["master_token"])

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json(
            {"tipo": "combate_accion", "datos": {"accion": "atacar", "enemigo_id": "contrabandista_1"}}
        )
        resultado = ws.receive_json()["datos"]
        assert resultado["personaje_id"] == kara["personaje"]["id"]
        assert resultado["personaje_nombre"] == "Kara la Espadachina"


@pytest.mark.skip(reason="vocabulario de acciones de combate retirado — rehacer en la Fase 3")
def test_huir_identifica_al_personaje_que_huye(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    _entrar_en_combate(client, codigo, sala["master_token"])

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"tipo": "combate_accion", "datos": {"accion": "huir"}})
        resultado = ws.receive_json()["datos"]
        assert resultado["personaje_id"] == kara["personaje"]["id"]
        assert resultado["personaje_nombre"] == "Kara la Espadachina"


@pytest.mark.skip(reason="vocabulario de acciones de combate retirado — rehacer en la Fase 3")
def test_negociar_identifica_al_personaje_que_negocia(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    _entrar_en_combate(client, codigo, sala["master_token"])

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"tipo": "combate_accion", "datos": {"accion": "negociar"}})
        resultado = ws.receive_json()["datos"]
        assert resultado["personaje_id"] == kara["personaje"]["id"]
        assert resultado["personaje_nombre"] == "Kara la Espadachina"


def test_usar_objeto_identifica_al_personaje_que_lo_usa(client, historia_cuervo_negro, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    client.post(
        f"/salas/{codigo}/personajes/{kara['personaje']['id']}/objetos",
        json={
            "objeto_id": "pocion_prueba",
            "nombre": "Poción de prueba",
            "consumible": True,
            "efecto": {"tipo": "curar_vida", "cantidad": 5},
        },
        headers={"Authorization": f"Bearer {sala['master_token']}"},
    )
    _entrar_en_combate(client, codigo, sala["master_token"])

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json(
            {"tipo": "combate_accion", "datos": {"accion": "objeto", "objeto_id": "pocion_prueba"}}
        )
        resultado = ws.receive_json()["datos"]
        assert resultado["personaje_id"] == kara["personaje"]["id"]
        assert resultado["personaje_nombre"] == "Kara la Espadachina"


@pytest.mark.skip(reason="vocabulario de acciones de combate retirado — rehacer en la Fase 3")
def test_lanzar_hechizo_identifica_al_personaje_que_lo_lanza(
    client, historia_cuervo_negro, d20_siempre_veinte
):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")
    _entrar_en_combate(client, codigo, sala["master_token"])

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
        resultado = ws.receive_json()["datos"]
        assert resultado["personaje_id"] == ilyana["personaje"]["id"]
        assert resultado["personaje_nombre"] == "Ilyana la Hechicera"
