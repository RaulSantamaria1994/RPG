"""Pruebas del diario de pistas: las flags narrativas (`requiere_flag`,
`flags_set_exito`/`flags_set_fallo`) son invisibles salvo lo que cuente el
texto del nodo. `_estado_publico` traduce las flags activas que la historia
documenta en `pistas` a un registro legible de "lo que sabéis", en el
orden en que se fueron descubriendo. Una flag sin texto documentado sigue
funcionando como mecanismo de desbloqueo, pero no aparece en el diario.
"""


def _crear_sala(client, historia_cuervo_negro, muerte_permanente=False):
    resp = client.post(
        "/salas",
        json={"master_nombre": "M", "historia_id": "cuervo_negro", "muerte_permanente": muerte_permanente},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_personaje(client, codigo, personaje_id="kara_la_espadachina", jugador_nombre="Ana"):
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


def test_diario_vacio_al_empezar(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        inicial = _recibir_hasta(ws, "estado_inicial")
        assert inicial["datos"]["diario"] == []


def test_flag_con_pista_documentada_aparece_en_el_diario(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws, client.websocket_connect(
        f"/ws/sala/{codigo}?token={sala['master_token']}"
    ) as ws_master:
        _recibir_hasta(ws, "estado_inicial")
        _recibir_hasta(ws_master, "estado_inicial")

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n009"}})
        _recibir_hasta(ws, "nodo_actualizado")
        _recibir_hasta(ws_master, "nodo_actualizado")

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
        actualizado = _recibir_hasta(ws, "nodo_actualizado")

        assert actualizado["datos"]["flags"]["sabe_plan"] is True
        assert actualizado["datos"]["diario"] == [
            {
                "flag": "sabe_plan",
                "texto": "Habéis escuchado las voces junto a las cajas selladas: ahora conocéis el plan que están discutiendo.",
            }
        ]


def test_flag_sin_pista_documentada_no_aparece_en_el_diario(client, historia_cuervo_negro, db):
    import uuid

    from sqlalchemy.orm.attributes import flag_modified

    from app.models.estado_sala import EstadoSala
    from app.models.sala import Sala

    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)

    sala_db = db.query(Sala).filter(Sala.codigo == codigo).one()
    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == sala_db.id).one()
    estado.flags = {**(estado.flags or {}), "flag_sin_texto": True}
    flag_modified(estado, "flags")
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws, client.websocket_connect(
        f"/ws/sala/{codigo}?token={sala['master_token']}"
    ) as ws_master:
        _recibir_hasta(ws, "estado_inicial")
        _recibir_hasta(ws_master, "estado_inicial")

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n002"}})
        actualizado = _recibir_hasta(ws, "nodo_actualizado")

        assert actualizado["datos"]["flags"]["flag_sin_texto"] is True
        assert actualizado["datos"]["diario"] == []


def test_diario_conserva_el_orden_en_que_se_descubrieron_las_pistas(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws, client.websocket_connect(
        f"/ws/sala/{codigo}?token={sala['master_token']}"
    ) as ws_master:
        _recibir_hasta(ws, "estado_inicial")
        _recibir_hasta(ws_master, "estado_inicial")

        # Primero una pista por fallo (alerta_guardias, en n006), después una
        # por éxito (sabe_plan, en n009) — el diario debe listar ambas en
        # ese mismo orden de descubrimiento, no por orden alfabético.
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n006"}})
        _recibir_hasta(ws, "nodo_actualizado")

        ws_master.send_json(
            {
                "tipo": "override_resultado",
                "datos": {
                    "personaje_id": kara["personaje"]["id"],
                    "palabra_clave": "forzar la puerta lateral",
                    "exito": False,
                },
            }
        )
        _recibir_hasta(ws, "nodo_actualizado")

        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n009"}})
        _recibir_hasta(ws, "nodo_actualizado")

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
        actualizado = _recibir_hasta(ws, "nodo_actualizado")

        assert [entrada["flag"] for entrada in actualizado["datos"]["diario"]] == [
            "alerta_guardias",
            "sabe_plan",
        ]
