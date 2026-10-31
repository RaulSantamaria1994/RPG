"""Pruebas del inventario común: los objetos pueden otorgarse en cualquier
tipo de nodo con solo llegar a él (no solo al éxito de una palabra clave de
un nodo interactivo), y el inventario de grupo es usable por cualquier
jugador en combate, sin necesidad de intercambiarlo antes a nadie.

Una prueba espera la "reacción" automática del enemigo tras usar un objeto
de ataque en combate, modelo que el motor PbtA retira por ahora (ver
docs/motor_pbta_plan.md) — queda `skip` hasta la Fase 3.
"""

import uuid

import pytest

from app.engine.validator import validar_historia
from app.models.estado_sala import EstadoSala
from app.models.historia import Historia


def _crear_sala_cuervo_negro(client, historia_cuervo_negro):
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


def _recibir_hasta(ws, tipo, maximo=20):
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


HISTORIA_SINTETICA = {
    "historia_id": "prueba_objetos_al_llegar",
    "titulo": "Prueba: objetos al llegar",
    "version": 1,
    "motor_version": "pbta-1",
    "nodo_inicial": "n_salida",
    "nodos": {
        "n_salida": {"tipo": "narrativo", "texto": "..", "es_final": False, "nodo_siguiente": "n_hallazgo"},
        "n_hallazgo": {
            "tipo": "narrativo",
            "texto": "Encontráis una llave oxidada en el suelo.",
            "es_final": False,
            "nodo_siguiente": "n_final",
            "objetos_otorgados": [
                {"objeto_id": "llave_oxidada", "nombre": "Llave oxidada"},
                {"objeto_id": "nota", "nombre": "Nota arrugada", "destino": "grupo"},
            ],
        },
        "n_final": {"tipo": "narrativo", "texto": "Fin.", "es_final": True, "tipo_final": "heroico"},
    },
}


def test_historia_sintetica_es_valida():
    assert validar_historia(HISTORIA_SINTETICA).valida


def test_objetos_otorgados_se_anuncian_y_llegan_al_inventario_de_grupo(client, db):
    resultado = validar_historia(HISTORIA_SINTETICA)
    assert resultado.valida, resultado.errores
    historia = Historia(
        historia_id=HISTORIA_SINTETICA["historia_id"],
        titulo=HISTORIA_SINTETICA["titulo"],
        version=1,
        contenido=HISTORIA_SINTETICA,
        validada=True,
    )
    db.add(historia)
    db.commit()

    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": historia.historia_id})
    assert resp.status_code == 201, resp.text
    sala = resp.json()
    codigo = sala["sala"]["codigo"]

    creado = _crear_personaje_generico(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={creado['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")

            ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_hallazgo"}})

            anuncio = _recibir_hasta(ws, "objetos_otorgados")
            assert anuncio["datos"]["destino"] == "grupo"
            ids = {o["objeto_id"] for o in anuncio["datos"]["objetos"]}
            assert ids == {"llave_oxidada", "nota"}

            actualizado = _recibir_hasta(ws, "nodo_actualizado")
            ids_estado = {o["objeto_id"] for o in actualizado["datos"]["inventario_grupo"]}
            assert ids_estado == {"llave_oxidada", "nota"}


HISTORIA_HECHIZO_AL_LLEGAR = {
    "historia_id": "prueba_hechizo_al_llegar",
    "titulo": "Prueba: hechizo al llegar",
    "version": 1,
    "motor_version": "pbta-1",
    "nodo_inicial": "n_salida",
    "nodos": {
        "n_salida": {"tipo": "narrativo", "texto": "..", "es_final": False, "nodo_siguiente": "n_grimorio"},
        "n_grimorio": {
            "tipo": "narrativo",
            "texto": "Descubrís un grimorio que arde sin consumirse.",
            "es_final": False,
            "nodo_siguiente": "n_final",
            "objetos_otorgados": [
                {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"},
            ],
        },
        "n_final": {"tipo": "narrativo", "texto": "Fin.", "es_final": True, "tipo_final": "heroico"},
    },
}


def test_objeto_otorgado_de_categoria_hechizo_se_aprende_en_vez_de_ir_al_inventario(client, db):
    resultado = validar_historia(HISTORIA_HECHIZO_AL_LLEGAR)
    assert resultado.valida, resultado.errores
    historia = Historia(
        historia_id=HISTORIA_HECHIZO_AL_LLEGAR["historia_id"],
        titulo=HISTORIA_HECHIZO_AL_LLEGAR["titulo"],
        version=1,
        contenido=HISTORIA_HECHIZO_AL_LLEGAR,
        validada=True,
    )
    db.add(historia)
    db.commit()

    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": historia.historia_id})
    assert resp.status_code == 201, resp.text
    sala = resp.json()
    codigo = sala["sala"]["codigo"]

    creado = _crear_personaje_generico(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={creado['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")

            ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_grimorio"}})

            anuncio = _recibir_hasta(ws, "objetos_otorgados")
            assert anuncio["datos"]["objetos"] == [
                {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"}
            ]

            actualizado_personaje = _recibir_hasta(ws, "personaje_actualizado")
            assert actualizado_personaje["datos"]["hechizos_conocidos"] == ["ignis_arcanus"]

            actualizado_nodo = _recibir_hasta(ws, "nodo_actualizado")
            assert actualizado_nodo["datos"]["inventario_grupo"] == []  # no es un objeto físico

    resp = client.get(f"/salas/{codigo}/personajes")
    assert resp.json()[0]["hechizos_conocidos"] == ["ignis_arcanus"]


def _crear_personaje_generico(client, codigo):
    resp = client.post(
        f"/salas/{codigo}/personajes/personalizado",
        json={
            "jugador_nombre": "Ana",
            "nombre": "Exploradora",
            "atributos": {"fuerza": 3, "astucia": 3, "voluntad": 3, "agilidad": 3},
            "habilidad_pasiva": "ninguna",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_usar_objeto_del_grupo_en_combate_no_requiere_tenerlo_en_propiedad(
    client, historia_cuervo_negro, db
):
    sala = _crear_sala_cuervo_negro(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    # El botiquín va directo al fondo común, nunca al inventario de Kara.
    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == uuid.UUID(sala["sala"]["id"])).first()
    estado.inventario_grupo = [
        {"objeto_id": "botiquin", "nombre": "Botiquín", "efecto": {"tipo": "curar_vida", "cantidad": 5}, "consumible": True}
    ]
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        _recibir_hasta(ws_master, "nodo_actualizado")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")

            resp = client.get(f"/salas/{codigo}/personajes")
            personaje = next(p for p in resp.json() if p["nombre"] == "Kara la Espadachina")
            assert personaje["inventario"] == []  # Kara nunca tuvo el botiquín en propiedad

            ws.send_json(
                {"tipo": "combate_accion", "datos": {"accion": "objeto", "objeto_id": "botiquin"}}
            )
            resultado = _recibir_hasta(ws, "combate_resultado")
            assert resultado["datos"]["accion"] == "objeto"
            assert resultado["datos"]["efecto"]["tipo"] == "curar_vida"

    db.refresh(estado)
    assert estado.inventario_grupo == []  # se consumió del fondo común


@pytest.mark.skip(reason="reacción automática del enemigo tras objeto retirada — rehacer en la Fase 3")
def test_usar_objeto_de_ataque_en_combate_hace_dano_y_provoca_reaccion(
    client, historia_cuervo_negro, db
):
    sala = _crear_sala_cuervo_negro(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_personaje(client, codigo, "kara_la_espadachina", "Ana")

    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == uuid.UUID(sala["sala"]["id"])).first()
    estado.inventario_grupo = [
        {"objeto_id": "daga_arrojadiza", "nombre": "Daga arrojadiza", "efecto": {"tipo": "dano", "cantidad": 4}, "consumible": True}
    ]
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        _recibir_hasta(ws_master, "nodo_actualizado")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")

            ws.send_json(
                {
                    "tipo": "combate_accion",
                    "datos": {"accion": "objeto", "objeto_id": "daga_arrojadiza", "enemigo_id": "contrabandista_1"},
                }
            )
            resultado = _recibir_hasta(ws, "combate_resultado")
            assert resultado["datos"]["accion"] == "objeto"
            assert resultado["datos"]["efecto"] == {"tipo": "dano", "cantidad": 4, "enemigo_id": "contrabandista_1"}

            # El objeto de ataque sí provoca la reacción inmediata del enemigo
            # implicado, igual que un ataque normal.
            reaccion = _recibir_hasta(ws, "combate_resultado")
            assert reaccion["datos"]["origen"] == "enemigo"

    db.refresh(estado)
    assert estado.inventario_grupo == []  # se consumió al usarla
