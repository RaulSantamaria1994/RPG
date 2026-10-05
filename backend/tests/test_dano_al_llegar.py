"""Pruebas de `dano_al_llegar`: un nodo (de cualquier tipo) puede restar
vida a todo el grupo por el simple hecho de llegar a él — una trampa, una
caída, un peligro narrativo — sin que medie ninguna tirada.
"""

import uuid

from app.engine.validator import validar_historia
from app.models.historia import Historia
from app.models.personaje import Personaje


def _recibir_hasta(ws, tipo, maximo=20):
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


def _crear_personaje_generico(client, codigo, jugador_nombre="Ana"):
    resp = client.post(
        f"/salas/{codigo}/personajes/personalizado",
        json={
            "jugador_nombre": jugador_nombre,
            "nombre": "Exploradora",
            "atributos": {"fuerza": 3, "astucia": 3, "voluntad": 3, "agilidad": 3},
            "habilidad_pasiva": "ninguna",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


HISTORIA_TRAMPA = {
    "historia_id": "prueba_dano_al_llegar",
    "titulo": "Prueba: daño al llegar",
    "version": 1,
    "nodo_inicial": "n_salida",
    "nodos": {
        "n_salida": {"tipo": "narrativo", "texto": "..", "es_final": False, "nodo_siguiente": "n_trampa"},
        "n_trampa": {
            "tipo": "narrativo",
            "texto": "El suelo cede bajo vuestros pies.",
            "es_final": False,
            "nodo_siguiente": "n_final",
            "dano_al_llegar": {"cantidad": 4},
        },
        "n_final": {"tipo": "narrativo", "texto": "Fin.", "es_final": True, "tipo_final": "heroico"},
    },
}

HISTORIA_TRAMPA_MORTAL = {
    **HISTORIA_TRAMPA,
    "historia_id": "prueba_dano_al_llegar_mortal",
    "nodo_muerte_total": "n_muerte_total",
    "nodos": {
        **HISTORIA_TRAMPA["nodos"],
        "n_muerte_total": {"tipo": "narrativo", "texto": "Todos caéis.", "es_final": True, "tipo_final": "muerte_total"},
    },
}


def test_historias_sinteticas_son_validas():
    assert validar_historia(HISTORIA_TRAMPA).valida
    assert validar_historia(HISTORIA_TRAMPA_MORTAL).valida


def _crear_sala_con_historia(client, db, contenido, muerte_permanente=False):
    resultado = validar_historia(contenido)
    assert resultado.valida, resultado.errores
    historia = Historia(
        historia_id=contenido["historia_id"],
        titulo=contenido["titulo"],
        version=1,
        contenido=contenido,
        validada=True,
    )
    db.add(historia)
    db.commit()

    resp = client.post(
        "/salas",
        json={
            "master_nombre": "M",
            "historia_id": historia.historia_id,
            "muerte_permanente": muerte_permanente,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_dano_al_llegar_se_anuncia_y_resta_vida_a_todo_el_grupo(client, db):
    sala = _crear_sala_con_historia(client, db, HISTORIA_TRAMPA)
    codigo = sala["sala"]["codigo"]

    kara = _crear_personaje_generico(client, codigo, "Ana")
    ana = _crear_personaje_generico(client, codigo, "Bob")

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")

            ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_trampa"}})

            anuncio = _recibir_hasta(ws, "dano_al_llegar")
            assert anuncio["datos"]["cantidad"] == 4
            assert set(anuncio["datos"]["afectados"]) == {kara["personaje"]["id"], ana["personaje"]["id"]}

            actualizado_nodo = _recibir_hasta(ws, "nodo_actualizado")
            assert actualizado_nodo["datos"]["nodo_actual_id"] == "n_trampa"

    resp = client.get(f"/salas/{codigo}/personajes")
    vidas = {p["id"]: p["vida_actual"] for p in resp.json()}
    assert vidas[kara["personaje"]["id"]] == kara["personaje"]["vida_actual"] - 4
    assert vidas[ana["personaje"]["id"]] == ana["personaje"]["vida_actual"] - 4


def test_dano_al_llegar_sin_el_campo_no_afecta_la_vida(client, db):
    sala = _crear_sala_con_historia(client, db, HISTORIA_TRAMPA)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje_generico(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_salida"}})
        actualizado = _recibir_hasta(ws_master, "nodo_actualizado")
        assert actualizado["datos"]["nodo_actual_id"] == "n_salida"

    resp = client.get(f"/salas/{codigo}/personajes")
    assert resp.json()[0]["vida_actual"] == kara["personaje"]["vida_actual"]


def test_dano_al_llegar_mata_a_todo_el_grupo_y_salta_a_muerte_total(client, db):
    sala = _crear_sala_con_historia(client, db, HISTORIA_TRAMPA_MORTAL, muerte_permanente=True)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje_generico(client, codigo)

    p = db.get(Personaje, uuid.UUID(kara["personaje"]["id"]))
    p.vida_actual = 2
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")

            ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_trampa"}})

            anuncio = _recibir_hasta(ws, "dano_al_llegar")
            assert anuncio["datos"]["afectados"] == [kara["personaje"]["id"]]

            actualizado_personaje = _recibir_hasta(ws, "personaje_actualizado")
            assert actualizado_personaje["datos"]["estado"] == "muerto"
            assert actualizado_personaje["datos"]["vida_actual"] == 0

            final = _recibir_hasta(ws, "nodo_actualizado")
            assert final["datos"]["nodo_actual_id"] == "n_muerte_total"
            assert final["datos"]["finalizada"] is True
            assert final["datos"]["tipo_final"] == "muerte_total"
