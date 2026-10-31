from app.engine.dice import Banda, ResultadoTirada, banda_de, resolver_tirada
from app.engine.movidas import modificador_de
from app.engine.resolver import (
    aplicar_dano,
    aplicar_dano_al_llegar,
    aplicar_resultado,
    avanzar_a_nodo,
    otorgar_objeto,
    resolver_via_movida,
)
from app.engine.validator import validar_historia
from app.models.estado_sala import EstadoSala
from app.models.personaje import Personaje


def test_validar_historia_cuervo_negro_es_valida(contenido_cuervo_negro):
    resultado = validar_historia(contenido_cuervo_negro)
    assert resultado.valida
    assert resultado.errores == []


def test_validar_detecta_nodo_huerfano():
    contenido = {
        "historia_id": "x",
        "titulo": "x",
        "motor_version": "pbta-1",
        "nodo_inicial": "a",
        "nodos": {
            "a": {"tipo": "narrativo", "texto": "..", "es_final": True, "tipo_final": "heroico"},
            "b": {"tipo": "narrativo", "texto": "..", "es_final": True, "tipo_final": "heroico"},
        },
    }
    resultado = validar_historia(contenido)
    assert not resultado.valida
    assert any("inalcanzable" in e for e in resultado.errores)


def test_validar_detecta_referencia_rota():
    contenido = {
        "historia_id": "x",
        "titulo": "x",
        "motor_version": "pbta-1",
        "nodo_inicial": "a",
        "nodos": {
            "a": {"tipo": "narrativo", "texto": "..", "nodo_siguiente": "no_existe", "es_final": False},
        },
    }
    resultado = validar_historia(contenido)
    assert not resultado.valida
    assert any("inexistente" in e for e in resultado.errores)


def test_validar_detecta_camino_sin_final():
    contenido = {
        "historia_id": "x",
        "titulo": "x",
        "motor_version": "pbta-1",
        "nodo_inicial": "a",
        "nodos": {
            "a": {"tipo": "narrativo", "texto": "..", "nodo_siguiente": "b", "es_final": False},
            "b": {"tipo": "narrativo", "texto": "..", "nodo_siguiente": "a", "es_final": False},
        },
    }
    resultado = validar_historia(contenido)
    assert not resultado.valida
    assert any("ningún camino hacia un nodo final" in e for e in resultado.errores)


# --------------------------------------------------------------- dados (2d6)

def test_banda_de_umbrales():
    assert banda_de(10) == Banda.EXITO
    assert banda_de(12) == Banda.EXITO
    assert banda_de(9) == Banda.EXITO_CON_COSTE
    assert banda_de(7) == Banda.EXITO_CON_COSTE
    assert banda_de(6) == Banda.FALLO
    assert banda_de(2) == Banda.FALLO


def test_resolver_tirada_sin_modificador(monkeypatch):
    valores = iter([5, 4])  # d6=6, d6=5 (randbelow(6) devuelve 0-5)
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    r = resolver_tirada(modificador=0)
    assert r.dados == (6, 5)
    assert r.total == 11
    assert r.banda == Banda.EXITO
    assert r.exito is True


def test_resolver_tirada_7_9_es_exito_con_coste(monkeypatch):
    valores = iter([3, 2])  # d6=4, d6=3 -> 7
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    r = resolver_tirada(modificador=0)
    assert r.total == 7
    assert r.banda == Banda.EXITO_CON_COSTE
    assert r.exito is True  # el 7-9 cuenta como éxito: avanza igual que el 10+


def test_resolver_tirada_6_menos_es_fallo(monkeypatch):
    valores = iter([0, 0])  # d6=1, d6=1 -> 2
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    r = resolver_tirada(modificador=0)
    assert r.total == 2
    assert r.banda == Banda.FALLO
    assert r.exito is False


def test_modificador_de_convierte_valor_1_a_5_en_modificador_menos2_a_mas2():
    personaje = _personaje_de_prueba(fuerza=1, astucia=3, voluntad=5)
    assert modificador_de(personaje, "fuerza") == -2
    assert modificador_de(personaje, "astucia") == 0
    assert modificador_de(personaje, "voluntad") == 2


def test_resolver_via_movida_usa_la_caracteristica_de_la_movida(monkeypatch):
    valores = iter([3, 3])  # d6=4, d6=4 -> 8, + modificador
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje_de_prueba(fuerza=5)  # modificador +2
    palabra = {"texto": "Golpear al centinela", "movida": "golpear"}
    r = resolver_via_movida(palabra, personaje)
    assert r.modificador == 2
    assert r.total == 10
    assert r.banda == Banda.EXITO


def test_resolver_via_movida_gasta_suerte_para_convertir_un_fallo_en_exito(monkeypatch):
    valores = iter([0, 0])  # d6=1, d6=1 -> 2, fallo seguro con modificador 0
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje_de_prueba(voluntad=3)  # modificador 0
    palabra = {"texto": "Aguantar", "movida": "actuar_bajo_presion"}

    r = resolver_via_movida(palabra, personaje, usar_suerte=True)

    assert r.banda == Banda.EXITO
    assert personaje.puntos_suerte_actual == 6  # gastó uno de los 7 iniciales


def test_resolver_via_movida_no_gasta_suerte_si_no_hacia_falta(monkeypatch):
    valores = iter([5, 5])  # d6=6, d6=6 -> 12, éxito seguro
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    personaje = _personaje_de_prueba(voluntad=3)
    palabra = {"texto": "Aguantar", "movida": "actuar_bajo_presion"}

    resolver_via_movida(palabra, personaje, usar_suerte=True)

    assert personaje.puntos_suerte_actual == 7  # no gastó nada


# ------------------------------------------------------------- aplicar_dano

def test_aplicar_dano_resta_de_la_barra_de_7():
    personaje = _personaje_de_prueba(vida_actual=7)
    aplicado = aplicar_dano(personaje, 3)
    assert aplicado == 3
    assert personaje.vida_actual == 4


def test_aplicar_dano_lo_reduce_la_armadura_equipada():
    personaje = _personaje_de_prueba(vida_actual=7, armadura_equipada={"reduccion_dano": 2})
    aplicado = aplicar_dano(personaje, 3)
    assert aplicado == 1
    assert personaje.vida_actual == 6


def test_aplicar_dano_no_baja_de_cero_y_deja_inconsciente():
    personaje = _personaje_de_prueba(vida_actual=2)
    aplicar_dano(personaje, 5)
    assert personaje.vida_actual == 0
    assert personaje.estado == "inconsciente"


def test_aplicar_dano_mata_con_muerte_permanente():
    personaje = _personaje_de_prueba(vida_actual=2)
    aplicar_dano(personaje, 5, muerte_permanente=True)
    assert personaje.estado == "muerto"


# ---------------------------------------------------------- aplicar_resultado

def test_aplicar_resultado_10_mas_no_aplica_ningun_coste():
    personaje = _personaje_de_prueba(vida_actual=7)
    estado = _estado_de_prueba()
    palabra = {"texto": "t", "movida": "golpear", "nodo_exito": "a", "nodo_fallo": "b"}
    resultado = ResultadoTirada(dados=(6, 6), modificador=0, total=12, banda=Banda.EXITO)

    cambios = aplicar_resultado("n1", palabra, resultado, estado, personaje)

    assert cambios["dano_aplicado"] == 0
    assert cambios["nodo_destino"] == "a"
    assert personaje.vida_actual == 7


def test_aplicar_resultado_7_9_aplica_el_coste_por_defecto_de_la_movida():
    """'golpear' trae un coste por defecto de 1 de daño en el 7-9 (ver
    app/engine/movidas.py)."""
    personaje = _personaje_de_prueba(vida_actual=7)
    estado = _estado_de_prueba()
    palabra = {"texto": "t", "movida": "golpear", "nodo_exito": "a", "nodo_fallo": "b"}
    resultado = ResultadoTirada(dados=(4, 4), modificador=0, total=8, banda=Banda.EXITO_CON_COSTE)

    cambios = aplicar_resultado("n1", palabra, resultado, estado, personaje)

    assert cambios["dano_aplicado"] == 1
    assert cambios["nodo_destino"] == "a"  # el 7-9 sigue siendo éxito
    assert personaje.vida_actual == 6


def test_aplicar_resultado_7_9_respeta_coste_parcial_de_la_palabra_clave():
    personaje = _personaje_de_prueba(vida_actual=7)
    estado = _estado_de_prueba()
    palabra = {
        "texto": "t",
        "movida": "investigar",  # sin coste por defecto
        "nodo_exito": "a",
        "nodo_fallo": "b",
        "coste_parcial": {"tipo": "dano", "cantidad": 2},
    }
    resultado = ResultadoTirada(dados=(4, 4), modificador=0, total=8, banda=Banda.EXITO_CON_COSTE)

    cambios = aplicar_resultado("n1", palabra, resultado, estado, personaje)

    assert cambios["dano_aplicado"] == 2
    assert personaje.vida_actual == 5


def test_aplicar_resultado_fallo_lleva_a_nodo_fallo_y_aplica_dano_fallo():
    personaje = _personaje_de_prueba(vida_actual=7)
    estado = _estado_de_prueba()
    palabra = {
        "texto": "t",
        "movida": "golpear",
        "nodo_exito": "a",
        "nodo_fallo": "b",
        "dano_fallo": {"cantidad": 3},
    }
    resultado = ResultadoTirada(dados=(1, 1), modificador=0, total=2, banda=Banda.FALLO)

    cambios = aplicar_resultado("n1", palabra, resultado, estado, personaje)

    assert cambios["dano_aplicado"] == 3
    assert cambios["nodo_destino"] == "b"
    assert personaje.vida_actual == 4


def _personaje_de_prueba(**overrides) -> Personaje:
    base = dict(
        sala_id=None,
        jugador_nombre="a",
        nombre="a",
        fuerza=1,
        astucia=1,
        voluntad=1,
        agilidad=1,
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


def _estado_de_prueba() -> EstadoSala:
    return EstadoSala(sala_id=None, nodo_actual_id="n1", flags={}, palabras_clave_usadas=[], inventario_grupo=[])


def test_otorgar_objeto_sin_destino_explicito_usa_el_defecto_grupo():
    estado = _estado_de_prueba()
    item = otorgar_objeto({"objeto_id": "llave", "nombre": "Llave"}, estado, None, destino_defecto="grupo")

    assert item == {"objeto_id": "llave", "nombre": "Llave"}
    assert estado.inventario_grupo == [{"objeto_id": "llave", "nombre": "Llave"}]


def test_otorgar_objeto_con_destino_personaje_explicito_va_al_personaje():
    personaje = _personaje_de_prueba()
    estado = _estado_de_prueba()
    otorgar_objeto(
        {"objeto_id": "diario", "nombre": "Diario", "destino": "personaje"},
        estado,
        personaje,
        destino_defecto="grupo",
    )

    assert estado.inventario_grupo == []
    assert personaje.inventario == [{"objeto_id": "diario", "nombre": "Diario"}]


def test_otorgar_objeto_arma_copia_bono_dano():
    estado = _estado_de_prueba()
    item = otorgar_objeto(
        {"objeto_id": "machete", "nombre": "Machete", "categoria": "arma", "bono_dano": 3},
        estado,
        None,
        destino_defecto="grupo",
    )
    assert item["bono_dano"] == 3


def test_otorgar_objeto_armadura_copia_reduccion_dano():
    estado = _estado_de_prueba()
    item = otorgar_objeto(
        {"objeto_id": "chaleco", "nombre": "Chaleco", "categoria": "armadura", "reduccion_dano": 2},
        estado,
        None,
        destino_defecto="grupo",
    )
    assert item["reduccion_dano"] == 2


def test_avanzar_a_nodo_otorga_objetos_al_grupo_con_solo_llegar():
    """Cualquier nodo (narrativo, interactivo o de combate) puede regalar
    objetos al grupo por el simple hecho de llegar a él — a diferencia de
    `objeto_otorga_exito`, que depende del éxito de una palabra clave."""
    estado = _estado_de_prueba()
    historia = {
        "nodos": {
            "n1": {
                "tipo": "narrativo",
                "texto": "Encontráis algo en el suelo.",
                "es_final": False,
                "nodo_siguiente": "n2",
                "objetos_otorgados": [
                    {"objeto_id": "llave_oxidada", "nombre": "Llave oxidada"},
                ],
            },
        }
    }

    resumen = avanzar_a_nodo(estado, historia, "n1")

    assert estado.inventario_grupo == [{"objeto_id": "llave_oxidada", "nombre": "Llave oxidada"}]
    assert resumen["objetos_otorgados"] == [{"objeto_id": "llave_oxidada", "nombre": "Llave oxidada"}]


def test_avanzar_a_nodo_sin_objetos_otorgados_no_toca_el_inventario():
    estado = _estado_de_prueba()
    historia = {
        "nodos": {"n1": {"tipo": "narrativo", "texto": "..", "es_final": False, "nodo_siguiente": "n2"}}
    }

    avanzar_a_nodo(estado, historia, "n1")

    assert estado.inventario_grupo == []


def test_otorgar_objeto_de_categoria_hechizo_no_va_al_inventario_sino_a_hechizos_conocidos():
    """Un "objeto" de categoría hechizo no es un objeto físico: representa
    aprender a lanzar ese hechizo, así que no debe acabar en ningún
    inventario."""
    estado = _estado_de_prueba()
    personaje = _personaje_de_prueba()

    item = otorgar_objeto(
        {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"},
        estado,
        personaje,
        destino_defecto="grupo",
    )

    assert item == {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"}
    assert estado.inventario_grupo == []
    assert personaje.inventario == []
    assert personaje.hechizos_conocidos == ["ignis_arcanus"]


def test_otorgar_objeto_de_categoria_hechizo_con_personajes_sala_lo_ensena_a_todo_el_grupo():
    estado = _estado_de_prueba()
    kara = _personaje_de_prueba(nombre="Kara")
    ana = _personaje_de_prueba(nombre="Ana", hechizos_conocidos=["luz_fantasma"])

    otorgar_objeto(
        {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"},
        estado,
        None,
        destino_defecto="grupo",
        personajes_sala=[kara, ana],
    )

    assert kara.hechizos_conocidos == ["ignis_arcanus"]
    # Ana ya conocía otro hechizo: el nuevo se añade sin perder el que ya tenía.
    assert ana.hechizos_conocidos == ["luz_fantasma", "ignis_arcanus"]


def test_otorgar_objeto_de_categoria_hechizo_no_lo_duplica_si_ya_se_conoce():
    estado = _estado_de_prueba()
    kara = _personaje_de_prueba(hechizos_conocidos=["ignis_arcanus"])

    otorgar_objeto(
        {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"},
        estado,
        None,
        destino_defecto="grupo",
        personajes_sala=[kara],
    )

    assert kara.hechizos_conocidos == ["ignis_arcanus"]


def test_avanzar_a_nodo_con_objeto_otorgado_de_categoria_hechizo_lo_ensena_al_llegar():
    estado = _estado_de_prueba()
    kara = _personaje_de_prueba()
    historia = {
        "nodos": {
            "n1": {
                "tipo": "narrativo",
                "texto": "Descubrís un grimorio ardiente.",
                "es_final": False,
                "nodo_siguiente": "n2",
                "objetos_otorgados": [
                    {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"},
                ],
            },
        }
    }

    resumen = avanzar_a_nodo(estado, historia, "n1", personajes_sala=[kara])

    assert resumen["objetos_otorgados"] == [
        {"objeto_id": "ignis_arcanus", "nombre": "Ignis Arcanus", "categoria": "hechizo"}
    ]
    assert estado.inventario_grupo == []
    assert kara.hechizos_conocidos == ["ignis_arcanus"]


def test_aplicar_dano_al_llegar_resta_vida_a_todo_el_grupo():
    kara = _personaje_de_prueba(vida_actual=7)
    ana = _personaje_de_prueba(vida_actual=4)

    resultado = aplicar_dano_al_llegar({"dano_al_llegar": {"cantidad": 3}}, [kara, ana])

    assert kara.vida_actual == 4
    assert ana.vida_actual == 1
    assert set(resultado["afectados"]) == {str(kara.id), str(ana.id)}
    assert resultado["cantidad"] == 3


def test_aplicar_dano_al_llegar_sin_el_campo_no_hace_nada():
    kara = _personaje_de_prueba(vida_actual=7)
    assert aplicar_dano_al_llegar({}, [kara]) is None
    assert kara.vida_actual == 7


def test_aplicar_dano_al_llegar_deja_inconsciente_sin_muerte_permanente():
    kara = _personaje_de_prueba(vida_actual=2)
    aplicar_dano_al_llegar({"dano_al_llegar": {"cantidad": 5}}, [kara], muerte_permanente=False)
    assert kara.vida_actual == 0
    assert kara.estado == "inconsciente"


def test_aplicar_dano_al_llegar_mata_con_muerte_permanente():
    kara = _personaje_de_prueba(vida_actual=2)
    aplicar_dano_al_llegar({"dano_al_llegar": {"cantidad": 5}}, [kara], muerte_permanente=True)
    assert kara.vida_actual == 0
    assert kara.estado == "muerto"


def test_aplicar_dano_al_llegar_ignora_a_quien_ya_esta_muerto():
    kara = _personaje_de_prueba(vida_actual=0, estado="muerto")
    ana = _personaje_de_prueba(vida_actual=5)

    resultado = aplicar_dano_al_llegar({"dano_al_llegar": {"cantidad": 3}}, [kara, ana])

    assert kara.vida_actual == 0  # no se le vuelve a aplicar nada
    assert ana.vida_actual == 2
    assert resultado["afectados"] == [str(ana.id)]


def test_avanzar_a_nodo_con_dano_al_llegar_resta_vida_sin_tirada():
    estado = _estado_de_prueba()
    kara = _personaje_de_prueba(vida_actual=7)
    historia = {
        "nodos": {
            "n1": {
                "tipo": "narrativo",
                "texto": "El suelo cede bajo vuestros pies.",
                "es_final": False,
                "nodo_siguiente": "n2",
                "dano_al_llegar": {"cantidad": 4},
            },
        }
    }

    resumen = avanzar_a_nodo(estado, historia, "n1", personajes_sala=[kara])

    assert resumen["dano_al_llegar"] == {"cantidad": 4, "afectados": [str(kara.id)]}
    assert kara.vida_actual == 3
