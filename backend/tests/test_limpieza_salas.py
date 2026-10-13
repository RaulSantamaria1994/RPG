"""Pruebas de la limpieza de salas abandonadas: una sala sin ninguna
actividad (ninguna petición REST ni mensaje WS que toque
`ultima_actividad_en`) durante más de `sala_expiracion_dias` se borra junto
con su estado y personajes; una sala con actividad reciente no se toca.
"""

from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.mantenimiento import limpiar_salas_expiradas
from app.models.estado_sala import EstadoSala
from app.models.personaje import Personaje
from app.models.sala import Sala

settings = get_settings()


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post(
        "/salas",
        json={"master_nombre": "M", "historia_id": "cuervo_negro"},
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


def _retrasar_actividad(db, codigo, ahora, dias):
    sala = db.query(Sala).filter(Sala.codigo == codigo).one()
    sala.ultima_actividad_en = ahora - timedelta(days=dias)
    db.commit()


def test_sala_con_actividad_reciente_no_se_borra(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    borradas = limpiar_salas_expiradas(db)

    assert borradas == 0
    assert db.query(Sala).filter(Sala.codigo == codigo).first() is not None


def test_sala_justo_en_el_limite_no_se_borra(client, historia_cuervo_negro, db):
    """El límite es estrictamente "más de" `sala_expiracion_dias`, no
    "al menos" — una sala que lleva exactamente ese tiempo sin actividad
    todavía no ha expirado."""
    ahora = datetime.now(timezone.utc)
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    _retrasar_actividad(db, codigo, ahora, settings.sala_expiracion_dias)

    borradas = limpiar_salas_expiradas(db, ahora=ahora)

    assert borradas == 0
    assert db.query(Sala).filter(Sala.codigo == codigo).first() is not None


def test_sala_sin_actividad_mas_del_limite_se_borra_con_todo_lo_que_cuelga(
    client, historia_cuervo_negro, db
):
    ahora = datetime.now(timezone.utc)
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    sala_id = sala["sala"]["id"]
    kara = _crear_personaje(client, codigo)

    _retrasar_actividad(db, codigo, ahora, settings.sala_expiracion_dias + 1)

    borradas = limpiar_salas_expiradas(db, ahora=ahora)

    assert borradas == 1
    assert db.query(Sala).filter(Sala.codigo == codigo).first() is None
    assert db.query(Personaje).filter(Personaje.id == kara["personaje"]["id"]).first() is None
    assert db.query(EstadoSala).filter(EstadoSala.sala_id == sala_id).first() is None


def test_solo_borra_las_salas_realmente_expiradas(client, historia_cuervo_negro, db):
    ahora = datetime.now(timezone.utc)
    activa = _crear_sala(client, historia_cuervo_negro)
    expirada = _crear_sala(client, historia_cuervo_negro)
    _retrasar_actividad(db, expirada["sala"]["codigo"], ahora, settings.sala_expiracion_dias + 10)

    borradas = limpiar_salas_expiradas(db, ahora=ahora)

    assert borradas == 1
    assert db.query(Sala).filter(Sala.codigo == activa["sala"]["codigo"]).first() is not None
    assert db.query(Sala).filter(Sala.codigo == expirada["sala"]["codigo"]).first() is None
