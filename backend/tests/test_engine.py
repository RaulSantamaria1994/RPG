from app.engine.dice import resolver_tirada, resolver_tirada_opuesta
from app.engine.validator import validar_historia


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
