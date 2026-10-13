"""`DELETE /salas/{codigo}` nunca se había probado: verifica que borra la
sala junto con todo lo que cuelga de ella por cascada (estado, personajes),
que solo el máster puede hacerlo, y que una sala inexistente da 404.
"""

from app.models.estado_sala import EstadoSala
from app.models.personaje import Personaje
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


def test_borrar_sala_la_elimina_junto_con_estado_y_personajes(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    sala_id = sala["sala"]["id"]
    kara = _crear_personaje(client, codigo)
    ilyana = _crear_personaje(client, codigo, "ilyana_la_hechicera", "Bob")

    resp = client.delete(
        f"/salas/{codigo}", headers={"Authorization": f"Bearer {sala['master_token']}"}
    )
    assert resp.status_code == 204, resp.text

    db.expire_all()
    assert db.query(Sala).filter(Sala.codigo == codigo).first() is None
    assert db.query(EstadoSala).filter(EstadoSala.sala_id == sala_id).first() is None
    assert db.query(Personaje).filter(Personaje.sala_id == sala_id).first() is None
    assert db.query(Personaje).filter(Personaje.id == kara["personaje"]["id"]).first() is None
    assert db.query(Personaje).filter(Personaje.id == ilyana["personaje"]["id"]).first() is None


def test_borrar_sala_requiere_ser_el_master(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo)

    resp = client.delete(
        f"/salas/{codigo}", headers={"Authorization": f"Bearer {kara['token']}"}
    )
    assert resp.status_code == 403, resp.text

    db.expire_all()
    assert db.query(Sala).filter(Sala.codigo == codigo).first() is not None


def test_borrar_sala_inexistente_da_404(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)

    resp = client.delete(
        "/salas/ZZZZZZ", headers={"Authorization": f"Bearer {sala['master_token']}"}
    )
    assert resp.status_code == 404
