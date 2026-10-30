"""Catálogo cerrado de las 8 movidas básicas (ver docs/motor_pbta_plan.md,
sección 2). Vive en el motor, no en cada historia: una palabra clave
referencia el id de una de estas, y de aquí sale tanto la característica
que se tira como el coste por defecto de un resultado 7-9. Una historia
puede sobreescribir ese coste por defecto con `coste_parcial` en la propia
palabra clave si hace falta uno distinto.

`caracteristica=None` marca una movida que no se tira contra las bandas
normales (hoy solo "ayudar": su propia resolución vive en
`websockets/handlers/interaccion.py`, no aquí).
"""

ATRIBUTOS_VALIDOS = ("fuerza", "astucia", "voluntad", "agilidad")

COSTE_DANO_LEVE = {"tipo": "dano", "cantidad": 1}

MOVIDAS = {
    "actuar_bajo_presion": {
        "nombre": "Actuar bajo presión",
        "caracteristica": "voluntad",
        "coste_parcial_defecto": COSTE_DANO_LEVE,
    },
    "convencer": {
        "nombre": "Convencer o manipular",
        "caracteristica": "voluntad",
        "coste_parcial_defecto": None,
    },
    "investigar": {
        "nombre": "Investigar",
        "caracteristica": "astucia",
        "coste_parcial_defecto": None,
    },
    "leer_el_peligro": {
        "nombre": "Leer el peligro",
        "caracteristica": "astucia",
        "coste_parcial_defecto": COSTE_DANO_LEVE,
    },
    "golpear": {
        "nombre": "Golpear",
        "caracteristica": "fuerza",
        "coste_parcial_defecto": COSTE_DANO_LEVE,
    },
    "proteger": {
        "nombre": "Proteger a alguien",
        "caracteristica": "fuerza",
        "coste_parcial_defecto": COSTE_DANO_LEVE,
    },
    "escabullirse": {
        "nombre": "Escabullirse",
        "caracteristica": "agilidad",
        "coste_parcial_defecto": COSTE_DANO_LEVE,
    },
    "ayudar": {
        "nombre": "Ayudar a otro",
        "caracteristica": None,
        "coste_parcial_defecto": None,
    },
}


def modificador_de(personaje, caracteristica: str) -> int:
    """valor (1-5) -> modificador (-2 a +2). Ver docs/motor_pbta_plan.md
    sección 1: fórmula confirmada con el usuario, no viene de ningún
    manual de PbtA."""
    return getattr(personaje, caracteristica) - 3
