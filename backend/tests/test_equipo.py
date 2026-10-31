"""Equipo de combate: cada personaje puede llevar un arma y un hechizo
(grimorio) equipados desde el inventario común. El arma suma un bono fijo
al daño del ataque normal; el grimorio permite lanzar ese hechizo en
combate aunque el personaje nunca lo haya aprendido. Equipar algo lo saca
del fondo común — solo puede llevarlo un personaje a la vez — y
desequipar lo devuelve.

Tres pruebas usan la acción de combate vieja ("atacar") o lanzar hechizo en
combate (fuera del motor PbtA por ahora) — quedan `skip`.
"""

import uuid

import pytest

from app.engine.validator import validar_historia
from app.models.estado_sala import EstadoSala
from app.models.historia import Historia
from app.models.personaje import Personaje


def _crear_sala(client, historia_cuervo_negro):
    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": "cuervo_negro"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _crear_kara(client, codigo):
    resp = client.post(
        f"/salas/{codigo}/personajes/pregenerado",
        json={"jugador_nombre": "Ana", "personaje_pregenerado_id": "kara_la_espadachina"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _recibir_hasta(ws, tipo, maximo=20):
    for _ in range(maximo):
        m = ws.receive_json()
        if m["tipo"] == tipo:
            return m
    raise AssertionError(f"no llegó un mensaje de tipo '{tipo}' tras {maximo} intentos")


ESPADA = {"objeto_id": "espada_rota", "nombre": "Espada rota", "categoria": "arma", "bono_dano": 3}
GRIMORIO = {"objeto_id": "grimorio_cuervo", "nombre": "Grimorio del cuervo", "categoria": "grimorio", "hechizo_id": "grito_de_cuervo"}
POCION = {"objeto_id": "pocion", "nombre": "Poción", "efecto": {"tipo": "curar_vida", "cantidad": 5}, "consumible": True}


def test_equipar_arma_la_saca_del_inventario_comun_y_la_pone_en_la_ranura(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)

    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == uuid.UUID(sala["sala"]["id"])).first()
    estado.inventario_grupo = [ESPADA]
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        _recibir_hasta(ws, "estado_inicial")
        ws.send_json({"tipo": "equipar_objeto", "datos": {"objeto_id": "espada_rota"}})

        aviso = _recibir_hasta(ws, "equipo_cambiado")
        assert aviso["datos"] == {
            "personaje_nombre": "Kara la Espadachina",
            "objeto_nombre": "Espada rota",
            "ranura": "arma",
            "accion": "equipar",
        }

        actualizado = _recibir_hasta(ws, "personaje_actualizado")
        assert actualizado["datos"]["arma_equipada"] == ESPADA

        nodo = _recibir_hasta(ws, "nodo_actualizado")
        assert nodo["datos"]["inventario_grupo"] == []

    db.refresh(estado)
    assert estado.inventario_grupo == []


@pytest.mark.skip(reason="acción 'atacar' retirada (ahora 'golpear') — rehacer en la Fase 3")
def test_el_bono_de_dano_del_arma_se_aplica_en_combate(client, historia_cuervo_negro, db, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)
    kara_id = uuid.UUID(kara["personaje"]["id"])

    personaje = db.get(Personaje, kara_id)
    personaje.arma_equipada = ESPADA
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        _recibir_hasta(ws_master, "nodo_actualizado")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")
            ws.send_json(
                {"tipo": "combate_accion", "datos": {"accion": "atacar", "enemigo_id": "contrabandista_1"}}
            )
            resultado = _recibir_hasta(ws, "combate_resultado")
            # Fuerza 5 → base 4 (5 // 2 + 2); con la espada (+3) suma 7.
            assert resultado["datos"]["dano_aplicado"] == 7


@pytest.mark.skip(reason="hechizos en combate fuera del motor PbtA por ahora — rehacer en la Fase 3")
def test_equipar_grimorio_permite_lanzar_un_hechizo_no_aprendido(client, historia_cuervo_negro, db, d20_siempre_veinte):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)
    kara_id = uuid.UUID(kara["personaje"]["id"])

    assert kara["personaje"]["hechizos_conocidos"] == []
    personaje = db.get(Personaje, kara_id)
    personaje.hechizo_equipado = GRIMORIO
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
                    "datos": {
                        "accion": "hechizo",
                        "hechizo_id": "grito_de_cuervo",
                        "objetivo_enemigo_id": "contrabandista_1",
                    },
                }
            )
            resultado = _recibir_hasta(ws, "combate_resultado")
            assert resultado["datos"]["accion"] == "hechizo"
            assert resultado["datos"]["efecto"]["tipo"] == "aturdido"


@pytest.mark.skip(reason="hechizos en combate fuera del motor PbtA por ahora — rehacer en la Fase 3")
def test_lanzar_hechizo_sin_conocerlo_ni_llevar_el_grimorio_falla(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_combate1"}})
        _recibir_hasta(ws_master, "nodo_actualizado")

        with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
            _recibir_hasta(ws, "estado_inicial")
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
            error = _recibir_hasta(ws, "error")
            assert error["datos"]["mensaje"] == "No conoces ese hechizo."


def test_desequipar_devuelve_el_objeto_al_inventario_comun(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)
    kara_id = uuid.UUID(kara["personaje"]["id"])

    personaje = db.get(Personaje, kara_id)
    personaje.arma_equipada = ESPADA
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        _recibir_hasta(ws, "estado_inicial")
        ws.send_json({"tipo": "desequipar_objeto", "datos": {"ranura": "arma"}})

        aviso = _recibir_hasta(ws, "equipo_cambiado")
        assert aviso["datos"]["accion"] == "desequipar"
        assert aviso["datos"]["ranura"] == "arma"

        actualizado = _recibir_hasta(ws, "personaje_actualizado")
        assert actualizado["datos"]["arma_equipada"] is None

        nodo = _recibir_hasta(ws, "nodo_actualizado")
        assert nodo["datos"]["inventario_grupo"] == [ESPADA]


def test_equipar_otra_arma_devuelve_la_anterior_al_fondo_comun(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)
    kara_id = uuid.UUID(kara["personaje"]["id"])

    personaje = db.get(Personaje, kara_id)
    personaje.arma_equipada = ESPADA
    OTRA = {"objeto_id": "maza_oxidada", "nombre": "Maza oxidada", "categoria": "arma", "bono_dano": 1}
    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == uuid.UUID(sala["sala"]["id"])).first()
    estado.inventario_grupo = [OTRA]
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        _recibir_hasta(ws, "estado_inicial")
        ws.send_json({"tipo": "equipar_objeto", "datos": {"objeto_id": "maza_oxidada"}})
        _recibir_hasta(ws, "equipo_cambiado")

        actualizado = _recibir_hasta(ws, "personaje_actualizado")
        assert actualizado["datos"]["arma_equipada"] == OTRA

        nodo = _recibir_hasta(ws, "nodo_actualizado")
        assert nodo["datos"]["inventario_grupo"] == [ESPADA]


def test_equipar_un_objeto_no_equipable_da_error(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)

    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == uuid.UUID(sala["sala"]["id"])).first()
    estado.inventario_grupo = [POCION]
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        _recibir_hasta(ws, "estado_inicial")
        ws.send_json({"tipo": "equipar_objeto", "datos": {"objeto_id": "pocion"}})
        error = _recibir_hasta(ws, "error")
        assert error["datos"]["mensaje"] == "Ese objeto no se puede equipar."


def test_equipar_un_objeto_que_no_esta_en_el_fondo_comun_da_error(client, historia_cuervo_negro):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]
    kara = _crear_kara(client, codigo)

    with client.websocket_connect(f"/ws/sala/{codigo}?token={kara['token']}") as ws:
        _recibir_hasta(ws, "estado_inicial")
        ws.send_json({"tipo": "equipar_objeto", "datos": {"objeto_id": "no_existe"}})
        error = _recibir_hasta(ws, "error")
        assert error["datos"]["mensaje"] == "Ese objeto no está en el inventario común."


HISTORIA_ARMA_Y_GRIMORIO_AL_LLEGAR = {
    "historia_id": "prueba_equipo_al_llegar",
    "titulo": "Prueba: arma y grimorio al llegar",
    "version": 1,
    "motor_version": "pbta-1",
    "nodo_inicial": "n_salida",
    "nodos": {
        "n_salida": {"tipo": "narrativo", "texto": "..", "es_final": False, "nodo_siguiente": "n_hallazgo"},
        "n_hallazgo": {
            "tipo": "narrativo",
            "texto": "Encontráis un machete oxidado y un cuaderno con anotaciones arcanas.",
            "es_final": False,
            "nodo_siguiente": "n_final",
            "objetos_otorgados": [
                {"objeto_id": "machete", "nombre": "Machete oxidado", "categoria": "arma", "bono_dano": 4},
                {
                    "objeto_id": "cuaderno",
                    "nombre": "Cuaderno arcano",
                    "categoria": "grimorio",
                    "hechizo_id": "grito_de_cuervo",
                },
            ],
        },
        "n_final": {"tipo": "narrativo", "texto": "Fin.", "es_final": True, "tipo_final": "heroico"},
    },
}


def test_un_arma_o_grimorio_otorgados_por_la_historia_llegan_con_su_bono_y_su_hechizo(client, db):
    # Reproduce el camino real de una recompensa narrativa (no una
    # inyección directa en BD): si `otorgar_objeto` no copiara bono_dano/
    # hechizo_id, el objeto llegaría al inventario común pero quedaría
    # mudo — equipable pero sin ningún efecto mecánico.
    resultado = validar_historia(HISTORIA_ARMA_Y_GRIMORIO_AL_LLEGAR)
    assert resultado.valida, resultado.errores
    historia = Historia(
        historia_id=HISTORIA_ARMA_Y_GRIMORIO_AL_LLEGAR["historia_id"],
        titulo=HISTORIA_ARMA_Y_GRIMORIO_AL_LLEGAR["titulo"],
        version=1,
        contenido=HISTORIA_ARMA_Y_GRIMORIO_AL_LLEGAR,
        validada=True,
    )
    db.add(historia)
    db.commit()

    resp = client.post("/salas", json={"master_nombre": "M", "historia_id": historia.historia_id})
    assert resp.status_code == 201, resp.text
    sala = resp.json()
    codigo = sala["sala"]["codigo"]

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws_master:
        _recibir_hasta(ws_master, "estado_inicial")
        ws_master.send_json({"tipo": "override_nodo", "datos": {"nodo_id": "n_hallazgo"}})

        actualizado = _recibir_hasta(ws_master, "nodo_actualizado")
        por_id = {o["objeto_id"]: o for o in actualizado["datos"]["inventario_grupo"]}
        assert por_id["machete"]["bono_dano"] == 4
        assert por_id["cuaderno"]["hechizo_id"] == "grito_de_cuervo"


def test_el_master_no_puede_equipar_objetos(client, historia_cuervo_negro, db):
    sala = _crear_sala(client, historia_cuervo_negro)
    codigo = sala["sala"]["codigo"]

    estado = db.query(EstadoSala).filter(EstadoSala.sala_id == uuid.UUID(sala["sala"]["id"])).first()
    estado.inventario_grupo = [ESPADA]
    db.commit()

    with client.websocket_connect(f"/ws/sala/{codigo}?token={sala['master_token']}") as ws:
        _recibir_hasta(ws, "estado_inicial")
        ws.send_json({"tipo": "equipar_objeto", "datos": {"objeto_id": "espada_rota"}})
        error = _recibir_hasta(ws, "error")
        assert error["datos"]["mensaje"] == "Solo un jugador puede equipar objetos."
