"""`Sala.ultima_actividad_en` es lo único que la limpieza de salas
expiradas mira para decidir qué borrar (ver `test_limpieza_salas.py`), así
que toda acción real sobre una sala debe refrescarlo — no solo abrir el
WebSocket, sino cada mensaje reconocido que se envíe por él, y no solo el
cierre explícito, sino cualquier otra escritura vía REST (crear personaje,
regenerar el código, el override de inventario del máster).
"""

from datetime import datetime, timedelta, timezone

from app.models.sala import Sala


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_personaje(client, codigo, personaje_id="kara_la_espadachina", jugador_nombre="Ana"):
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": jugador_nombre, "personaje_pregenerado_id": personaje_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _envejecer(db, codigo, dias=60):
    sala = db.query(Sala).filter(Sala.codigo == codigo).one()
    sala.ultima_actividad_en = datetime.now(timezone.utc) - timedelta(days=dias)
    db.commit()
    return sala.ultima_actividad_en


def _ultima_actividad(db, codigo):
    db.expire_all()
    return db.query(Sala).filter(Sala.codigo == codigo).one().ultima_actividad_en


def test_crear_personaje_actualiza_ultima_actividad(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    vieja = _envejecer(db, codigo)

    _crear_personaje(client, codigo)

    assert _ultima_actividad(db, codigo) > vieja


def test_regenerar_codigo_actualiza_ultima_actividad(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    vieja = _envejecer(db, codigo)

    resp = client.post(
        f"/salas/{codigo}/regenerar-codigo",
        headers={"Authorization": f"Bearer {sala['master_token']}"},
    )
    assert resp.status_code == 200, resp.text
    nuevo_codigo = resp.json()["codigo"]

    assert _ultima_actividad(db, nuevo_codigo) > vieja


def test_override_inventario_actualiza_ultima_actividad(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)
    vieja = _envejecer(db, codigo)

    resp = client.post(
        f"/salas/{codigo}/personajes/{kara['personaje']['id']}/objetos",
        json={"objeto_id": "amuleto_prueba", "nombre": "Amuleto de prueba"},
        headers={"Authorization": f"Bearer {sala['master_token']}"},
    )
    assert resp.status_code == 200, resp.text

    assert _ultima_actividad(db, codigo) > vieja


def test_cada_mensaje_ws_reconocido_actualiza_ultima_actividad(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        ws.receive_json()  # estado_inicial
        ws.receive_json()  # jugador_conectado (el propio máster, al broadcastearse su conexión)

        tras_conectar = _ultima_actividad(db, codigo)
        vieja = _envejecer(db, codigo)
        assert vieja < tras_conectar  # confirma que de verdad la hemos hecho retroceder

        # Un mensaje reconocido (aunque el personaje no exista y el handler
        # responda con un error) ya debe contar como actividad: lo que
        # importa es que alguien está ahí enviando acciones, no si la acción
        # concreta tuvo éxito.
        ws.send_json({"tipo": "marcar_activo", "datos": {"personaje_id": "no-existe"}})
        ws.receive_json()  # error

        assert _ultima_actividad(db, codigo) > vieja

        # Un segundo mensaje reconocido debe volver a adelantarla — no es
        # solo el primer mensaje de la conexión el que cuenta.
        vieja_segunda_vez = _envejecer(db, codigo)
        ws.send_json({"tipo": "marcar_activo", "datos": {"personaje_id": "no-existe"}})
        ws.receive_json()  # error
        assert _ultima_actividad(db, codigo) > vieja_segunda_vez

        # Un tipo de mensaje no reconocido, en cambio, no cuenta como
        # actividad — no llega a ningún manejador real.
        vieja_tercera_vez = _envejecer(db, codigo)
        ws.send_json({"tipo": "esto_no_existe", "datos": {}})
        ws.receive_json()  # error
        assert _ultima_actividad(db, codigo) == vieja_tercera_vez
