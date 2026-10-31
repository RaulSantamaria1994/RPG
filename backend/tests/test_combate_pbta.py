"""Pruebas del motor de combate PbtA (app/engine/combate.py): cada acción
se resuelve con una movida (2d6 + característica), y el contraataque del
enemigo, si lo hay, va dentro de la propia resolución — no hay un paso de
reacción aparte ni iniciativa de d20.
"""

from app.engine.combate import (
    avanzar_turno,
    enemigo_en_combate,
    evaluar_fin_combate,
    iniciar_combate,
    resolver_actuar_bajo_presion,
    resolver_escabullirse,
    resolver_golpear,
    resolver_proteger,
)
from app.models.personaje import Personaje


def _personaje(**overrides) -> Personaje:
    base = dict(
        sala_id=None,
        jugador_nombre="a",
        nombre="a",
        fuerza=5,
        astucia=3,
        voluntad=3,
        agilidad=3,
        habilidad_pasiva="x",
        vida_max=7,
        vida_actual=7,
        puntos_suerte_max=7,
        puntos_suerte_actual=7,
        mana_max=5,
        mana_actual=5,
        es_master=False,
        inventario=[],
        hechizos_conocidos=[],
        rasgos=[],
        arma_equipada=None,
        armadura_equipada=None,
        estado="activo",
    )
    base.update(overrides)
    return Personaje(**base)


def _nodo_combate(**enemigo_overrides) -> dict:
    enemigo = {"enemigo_id": "e1", "nombre": "Enemigo", "vida": 10, "dano": 3}
    enemigo.update(enemigo_overrides)
    return {"enemigos": [enemigo]}


def test_iniciar_combate_copia_enemigos_y_ordena_por_llegada():
    kara = _personaje(nombre="Kara")
    ana = _personaje(nombre="Ana")
    combate = iniciar_combate(_nodo_combate(), [kara, ana])

    assert combate["enemigos"][0]["vida"] == 10
    assert combate["enemigos"][0]["vida_max"] == 10
    assert combate["enemigos"][0]["derrotado"] is False
    assert combate["orden_iniciativa"] == [f"personaje:{kara.id}", f"personaje:{ana.id}"]
    assert combate["turno_index"] == 0
    assert combate["ronda"] == 1


def test_golpear_10_mas_hace_dano_sin_que_el_enemigo_conteste(monkeypatch):
    valores = iter([5, 5])  # d6=6, d6=6 -> 12 + mod(fuerza5->+2) = 14, 10+
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(fuerza=5, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(), [personaje])

    resultado = resolver_golpear(combate, personaje, "e1")

    assert resultado["tirada"]["banda"] == "exito"
    assert resultado["dano_a_enemigo"] == 1  # 1 base, sin arma
    assert resultado["dano_recibido"] == 0
    assert combate["enemigos"][0]["vida"] == 9
    assert personaje.vida_actual == 7


def test_golpear_7_9_hace_dano_pero_el_enemigo_contraataca(monkeypatch):
    valores = iter([2, 2])  # d6=3, d6=3 -> 6 + mod(+2) = 8, 7-9
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(fuerza=5, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(dano=3), [personaje])

    resultado = resolver_golpear(combate, personaje, "e1")

    assert resultado["tirada"]["banda"] == "exito_con_coste"
    assert resultado["dano_a_enemigo"] == 1
    assert resultado["dano_recibido"] == 3
    assert combate["enemigos"][0]["vida"] == 9
    assert personaje.vida_actual == 4


def test_golpear_6_menos_no_hace_dano_y_el_enemigo_contraataca(monkeypatch):
    valores = iter([0, 0])  # d6=1, d6=1 -> 2 + mod(+2) = 4, fallo
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(fuerza=5, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(dano=3), [personaje])

    resultado = resolver_golpear(combate, personaje, "e1")

    assert resultado["tirada"]["banda"] == "fallo"
    assert resultado["dano_a_enemigo"] == 0
    assert resultado["dano_recibido"] == 3
    assert combate["enemigos"][0]["vida"] == 10
    assert personaje.vida_actual == 4


def test_golpear_suma_el_bono_de_dano_del_arma_equipada(monkeypatch):
    valores = iter([5, 5])  # 10+
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(fuerza=5, arma_equipada={"bono_dano": 3})
    combate = iniciar_combate(_nodo_combate(), [personaje])

    resultado = resolver_golpear(combate, personaje, "e1")

    assert resultado["dano_a_enemigo"] == 4  # 1 base + 3 del arma


def test_golpear_derrota_al_enemigo_cuando_su_vida_llega_a_cero(monkeypatch):
    valores = iter([5, 5])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(fuerza=5, arma_equipada={"bono_dano": 5})
    combate = iniciar_combate(_nodo_combate(vida=4), [personaje])

    resultado = resolver_golpear(combate, personaje, "e1")

    assert resultado["enemigo_derrotado"] is True
    assert combate["enemigos"][0]["derrotado"] is True
    assert evaluar_fin_combate(combate) == "victoria"
    assert combate["terminado"] is True


def test_golpear_respeta_la_reduccion_de_la_armadura(monkeypatch):
    valores = iter([2, 2])  # 7-9
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(fuerza=5, vida_actual=7, armadura_equipada={"reduccion_dano": 2})
    combate = iniciar_combate(_nodo_combate(dano=3), [personaje])

    resultado = resolver_golpear(combate, personaje, "e1")

    assert resultado["dano_recibido"] == 1  # 3 de daño - 2 de armadura
    assert personaje.vida_actual == 6


def test_proteger_10_mas_nadie_recibe_dano(monkeypatch):
    valores = iter([5, 5])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    protector = _personaje(nombre="Protector", fuerza=5)
    protegido = _personaje(nombre="Protegido")
    combate = iniciar_combate(_nodo_combate(dano=3), [protector, protegido])

    resultado = resolver_proteger(combate, protector, protegido, "e1")

    assert resultado["dano_protector"] == 0
    assert resultado["dano_protegido"] == 0
    assert protector.vida_actual == 7
    assert protegido.vida_actual == 7


def test_proteger_7_9_el_protector_recibe_el_dano(monkeypatch):
    valores = iter([2, 2])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    protector = _personaje(nombre="Protector", fuerza=5)
    protegido = _personaje(nombre="Protegido")
    combate = iniciar_combate(_nodo_combate(dano=3), [protector, protegido])

    resultado = resolver_proteger(combate, protector, protegido, "e1")

    assert resultado["dano_protector"] == 3
    assert resultado["dano_protegido"] == 0
    assert protector.vida_actual == 4
    assert protegido.vida_actual == 7


def test_proteger_6_menos_el_protegido_recibe_el_dano(monkeypatch):
    valores = iter([0, 0])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    protector = _personaje(nombre="Protector", fuerza=5)
    protegido = _personaje(nombre="Protegido")
    combate = iniciar_combate(_nodo_combate(dano=3), [protector, protegido])

    resultado = resolver_proteger(combate, protector, protegido, "e1")

    assert resultado["dano_protector"] == 0
    assert resultado["dano_protegido"] == 3
    assert protector.vida_actual == 7
    assert protegido.vida_actual == 4


def test_escabullirse_10_mas_huye_sin_dano(monkeypatch):
    valores = iter([5, 5])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(agilidad=5)
    combate = iniciar_combate(_nodo_combate(dano=3), [personaje])

    resultado = resolver_escabullirse(combate, personaje)

    assert resultado["huido"] is True
    assert resultado["dano_recibido"] == 0


def test_escabullirse_7_9_huye_pero_recibe_dano(monkeypatch):
    valores = iter([2, 2, 0])  # tirada 7-9, luego randbelow para elegir enemigo reactivo
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(agilidad=5, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(dano=3), [personaje])

    resultado = resolver_escabullirse(combate, personaje)

    assert resultado["huido"] is True
    assert resultado["dano_recibido"] == 3
    assert personaje.vida_actual == 4


def test_escabullirse_6_menos_no_huye_y_recibe_dano(monkeypatch):
    valores = iter([0, 0, 0])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(agilidad=5, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(dano=3), [personaje])

    resultado = resolver_escabullirse(combate, personaje)

    assert resultado["huido"] is False
    assert resultado["dano_recibido"] == 3


def test_actuar_bajo_presion_7_9_aplica_un_punto_de_dano(monkeypatch):
    valores = iter([2, 2])  # d6=3, d6=3 -> 6 + mod(voluntad4->+1) = 7, 7-9
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(voluntad=4, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(), [personaje])

    resultado = resolver_actuar_bajo_presion(combate, personaje)

    assert resultado["dano_recibido"] == 1
    assert personaje.vida_actual == 6


def test_actuar_bajo_presion_10_mas_no_aplica_dano(monkeypatch):
    valores = iter([5, 5])
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje(voluntad=3, vida_actual=7)
    combate = iniciar_combate(_nodo_combate(), [personaje])

    resultado = resolver_actuar_bajo_presion(combate, personaje)

    assert resultado["dano_recibido"] == 0
    assert personaje.vida_actual == 7


def test_evaluar_fin_combate_none_si_queda_algun_enemigo_vivo():
    combate = iniciar_combate(_nodo_combate(), [_personaje()])
    assert evaluar_fin_combate(combate) is None
    assert combate["terminado"] is False


def test_avanzar_turno_vuelve_al_principio_y_suma_ronda():
    kara = _personaje(nombre="Kara")
    ana = _personaje(nombre="Ana")
    combate = iniciar_combate(_nodo_combate(), [kara, ana])

    avanzar_turno(combate)
    assert combate["turno_index"] == 1
    assert combate["ronda"] == 1

    avanzar_turno(combate)
    assert combate["turno_index"] == 0
    assert combate["ronda"] == 2


def test_enemigo_en_combate_devuelve_none_si_no_existe():
    combate = iniciar_combate(_nodo_combate(), [_personaje()])
    assert enemigo_en_combate(combate, "no_existe") is None
