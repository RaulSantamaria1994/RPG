"""`intercambio_proponer`/`intercambio_confirmar` (pasar un objeto propio a
otro jugador) no tenían ninguna prueba. Al escribirlas aparece un hueco
real: `_manejar_intercambio_confirmar` resolvía `origen` directamente del
`origen_personaje_id` que manda el cliente, sin comprobar que perteneciera
a esta sala — cualquiera podía robar un objeto de un personaje de OTRA
sala con solo conocer su id y el de uno de sus objetos. Corregido junto
con estas pruebas.
"""

import uuid

from app.models.personaje import Personaje


def _crear_sala(client, historia_cuervo_negro, master_nombre="M"):
    resp = client.post(
        "/salas", json={"master_nombre": master_nombre, "historia_id": "cuervo_negro"}
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


def _dar_objeto(client, codigo, personaje_id, master_token, objeto_id="amuleto_prueba"):
    resp = client.post(
        f"/salas/{codigo}/personajes/{personaje_id}/objetos",
        json={"objeto_id": objeto_id, "nombre": "Amuleto de prueba"},
        headers={"Authorization": f"Bearer {master_token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _recibir_hasta(ws, tipo, maximo=20):
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


def test_proponer_y_confirmar_mueve_el_objeto_entre_inventarios(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")
    _dar_objeto(client, codigo, kara["personaje"]["id"], sala["master_token"])

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws_kara, \
            client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws_ilyana:
        ws_kara.receive_json()  # estado_inicial
        ws_ilyana.receive_json()  # estado_inicial
        ws_ilyana.receive_json()  # jugador_conectado (la propia Ilyana)

        ws_kara.send_json(
            {
                "tipo": "intercambio_proponer",
                "datos": {
                    "objeto_id": "amuleto_prueba",
                    "destino_personaje_id": ilyana["personaje"]["id"],
                },
            }
        )
        propuesto = _recibir_hasta(ws_ilyana, "intercambio_propuesto")
        assert propuesto["datos"]["origen_personaje_id"] == kara["personaje"]["id"]
        assert propuesto["datos"]["objeto_id"] == "amuleto_prueba"
        assert propuesto["datos"]["destino_personaje_id"] == ilyana["personaje"]["id"]

        ws_ilyana.send_json(
            {
                "tipo": "intercambio_confirmar",
                "datos": {"origen_personaje_id": kara["personaje"]["id"], "objeto_id": "amuleto_prueba"},
            }
        )
        completado = _recibir_hasta(ws_kara, "intercambio_completado")
        assert completado["datos"]["origen_personaje_id"] == kara["personaje"]["id"]
        assert completado["datos"]["destino_personaje_id"] == ilyana["personaje"]["id"]
        assert completado["datos"]["objeto"]["objeto_id"] == "amuleto_prueba"

    resp = client.get(f"/salas/{codigo}/personajes")
    personajes = {p["id"]: p for p in resp.json()}
    assert all(o["objeto_id"] != "amuleto_prueba" for o in personajes[kara["personaje"]["id"]]["inventario"])
    assert any(
        o["objeto_id"] == "amuleto_prueba" for o in personajes[ilyana["personaje"]["id"]]["inventario"]
    )


def test_proponer_sin_tener_el_objeto_da_error(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.send_json(
            {
                "tipo": "intercambio_proponer",
                "datos": {"objeto_id": "no_lo_tengo", "destino_personaje_id": str(uuid.uuid4())},
            }
        )
        _recibir_hasta(ws, "error")


def test_el_master_no_puede_proponer_ni_confirmar_intercambios(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    _dar_objeto(client, codigo, kara["personaje"]["id"], sala["master_token"])

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        ws_master.receive_json()  # estado_inicial

        ws_master.send_json(
            {
                "tipo": "intercambio_proponer",
                "datos": {"objeto_id": "amuleto_prueba", "destino_personaje_id": kara["personaje"]["id"]},
            }
        )
        _recibir_hasta(ws_master, "error")

        ws_master.send_json(
            {
                "tipo": "intercambio_confirmar",
                "datos": {"origen_personaje_id": kara["personaje"]["id"], "objeto_id": "amuleto_prueba"},
            }
        )
        _recibir_hasta(ws_master, "error")


def test_confirmar_objeto_ya_entregado_da_error(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={ilyana['token']}") as ws:
        ws.receive_json()  # estado_inicial
        # Kara nunca tuvo ese objeto: no está en su inventario.
        ws.send_json(
            {
                "tipo": "intercambio_confirmar",
                "datos": {"origen_personaje_id": kara["personaje"]["id"], "objeto_id": "amuleto_prueba"},
            }
        )
        _recibir_hasta(ws, "error")


def test_confirmar_con_personaje_de_otra_sala_no_roba_el_objeto(client, historia_cuervo_negro, db):
    """El hueco real que motivó esta prueba: antes de la corrección, bastaba
    con conocer el id de un personaje de OTRA sala y el id de uno de sus
    objetos para que `intercambio_confirmar` se lo transfiriera a un
    personaje de esta sala."""
    sala_victima = _crear_sala(client, historia_cuervo_negro, master_nombre="Víctima")
    victima = _crear_personaje(
        client, sala_victima["sala"]["codigo"], "kara_la_espadachina", "Víctima"
    )
    _dar_objeto(
        client,
        sala_victima["sala"]["codigo"],
        victima["personaje"]["id"],
        sala_victima["master_token"],
        objeto_id="objeto_codiciado",
    )

    sala_atacante = _crear_sala(client, historia_cuervo_negro, master_nombre="Atacante")
    atacante = _crear_personaje(
        client, sala_atacante["sala"]["codigo"], "kara_la_espadachina", "Atacante"
    )

    with client.websocket_connect(
        f"/ws/sala/{sala_atacante['sala']['codigo']}?token={atacante['token']}"
    ) as ws:
        ws.receive_json()  # estado_inicial
        ws.send_json(
            {
                "tipo": "intercambio_confirmar",
                "datos": {
                    "origen_personaje_id": victima["personaje"]["id"],
                    "objeto_id": "objeto_codiciado",
                },
            }
        )
        _recibir_hasta(ws, "error")

    victima_actual = db.get(Personaje, uuid.UUID(victima["personaje"]["id"]))
    assert any(o["objeto_id"] == "objeto_codiciado" for o in (victima_actual.inventario or []))
    atacante_actual = db.get(Personaje, uuid.UUID(atacante["personaje"]["id"]))
    assert not any(o["objeto_id"] == "objeto_codiciado" for o in (atacante_actual.inventario or []))
