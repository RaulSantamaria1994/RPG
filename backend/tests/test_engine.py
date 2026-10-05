from app.engine.dice import resolver_tirada, resolver_tirada_opuesta
from app.engine.resolver import _tiene_ventaja, aplicar_resultado, avanzar_a_nodo, otorgar_objeto
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
        "nodo_inicial": "a",
        "nodos": {
            "a": {"tipo": "narrativo", "texto": "..", "nodo_siguiente": "b", "es_final": False},
            "b": {"tipo": "narrativo", "texto": "..", "nodo_siguiente": "a", "es_final": False},
        },
    }
    resultado = validar_historia(contenido)
    assert not resultado.valida
    assert any("ningún camino hacia un nodo final" in e for e in resultado.errores)


def test_resolver_tirada_exito_y_fallo(monkeypatch):
    monkeypatch.setattr("secrets.randbelow", lambda n: 19)  # d20 = 20
    r = resolver_tirada(modificador=2, dificultad=15)
    assert r.dado == 20
    assert r.total == 22
    assert r.exito is True

    monkeypatch.setattr("secrets.randbelow", lambda n: 0)  # d20 = 1
    r = resolver_tirada(modificador=2, dificultad=15)
    assert r.dado == 1
    assert r.exito is False


def test_resolver_tirada_ventaja_toma_el_mejor_dado(monkeypatch):
    valores = iter([0, 19])  # d20 = 1, luego d20 = 20
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    r = resolver_tirada(modificador=0, dificultad=10, ventaja=True)
    assert r.dado == 20
    assert r.dado_descartado == 1


def test_resolver_tirada_opuesta_gana_mayor_total(monkeypatch):
    valores = iter([19, 0])  # jugador saca 20, rival saca 1
    monkeypatch.setattr("secrets.randbelow", lambda n: next(valores))
    resultado = resolver_tirada_opuesta(modificador_jugador=0, modificador_rival=0)
    assert resultado["exito"] is True


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
        vida_max=10,
        vida_actual=10,
        mana_max=5,
        mana_actual=5,
        es_master=False,
        inventario=[],
        hechizos_conocidos=[],
        rasgos=[],
        estado="activo",
    )
    base.update(overrides)
    return Personaje(**base)


def _estado_de_prueba() -> EstadoSala:
    return EstadoSala(sala_id=None, nodo_actual_id="n1", flags={}, palabras_clave_usadas=[], inventario_grupo=[])


def test_aplicar_resultado_dano_fallo_resta_vida():
    personaje = _personaje_de_prueba()
    estado = _estado_de_prueba()
    palabra = {
        "texto": "t",
        "dificultad": 12,
        "atributo": "astucia",
        "nodo_exito": "a",
        "nodo_fallo": "b",
        "dano_fallo": {"cantidad": 3},
    }

    cambios = aplicar_resultado("n1", palabra, False, estado, personaje)

    assert cambios["dano_aplicado"] == 3
    assert personaje.vida_actual == 7
    assert personaje.estado == "activo"


def test_aplicar_resultado_dano_fallo_no_baja_de_cero_y_deja_inconsciente():
    personaje = _personaje_de_prueba(vida_actual=2)
    estado = _estado_de_prueba()
    palabra = {
        "texto": "t",
        "dificultad": 12,
        "atributo": "astucia",
        "nodo_exito": "a",
        "nodo_fallo": "b",
        "dano_fallo": {"cantidad": 5},
    }

    cambios = aplicar_resultado("n1", palabra, False, estado, personaje)

    assert cambios["dano_aplicado"] == 5
    assert personaje.vida_actual == 0
    assert personaje.estado == "inconsciente"


def test_aplicar_resultado_exito_no_aplica_dano_fallo():
    personaje = _personaje_de_prueba()
    estado = _estado_de_prueba()
    palabra = {
        "texto": "t",
        "dificultad": 12,
        "atributo": "astucia",
        "nodo_exito": "a",
        "nodo_fallo": "b",
        "dano_fallo": {"cantidad": 3},
    }

    cambios = aplicar_resultado("n1", palabra, True, estado, personaje)

    assert cambios["dano_aplicado"] == 0
    assert personaje.vida_actual == 10


def test_tiene_ventaja_reconoce_objeto_en_inventario_de_grupo():
    personaje = _personaje_de_prueba()
    estado = _estado_de_prueba()
    estado.inventario_grupo = [{"objeto_id": "prueba", "nombre": "Prueba del patrón"}]
    palabra = {"texto": "t", "ventaja_si_objeto": "prueba"}

    assert _tiene_ventaja(palabra, personaje, estado) is True


def test_tiene_ventaja_falso_sin_el_objeto_en_ningun_inventario():
    personaje = _personaje_de_prueba()
    estado = _estado_de_prueba()
    palabra = {"texto": "t", "ventaja_si_objeto": "prueba"}

    assert _tiene_ventaja(palabra, personaje, estado) is False


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
