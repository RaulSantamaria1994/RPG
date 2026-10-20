"""Construcción de personajes a partir del JSON de la historia: pregenerados
tal cual, o personalizados repartiendo un pool fijo de puntos.
"""

ATRIBUTOS = ("fuerza", "astucia", "voluntad", "agilidad")

PUNTOS_PERSONALIZADO_TOTAL = 12
PUNTOS_PERSONALIZADO_MIN = 1
PUNTOS_PERSONALIZADO_MAX = 5

VIDA_BASE = 20
MANA_BASE = 10


class ErrorCreacionPersonaje(Exception):
    pass


def construir_pregenerado(historia_contenido: dict, personaje_pregenerado_id: str) -> dict:
    for candidato in historia_contenido.get("personajes_pregenerados", []) or []:
        if candidato["id"] == personaje_pregenerado_id:
            return {
                "nombre": candidato["nombre"],
                "origen": "pregenerado",
                "personaje_pregenerado_id": candidato["id"],
                "trasfondo": candidato.get("trasfondo"),
                "fuerza": candidato["atributos"]["fuerza"],
                "astucia": candidato["atributos"]["astucia"],
                "voluntad": candidato["atributos"]["voluntad"],
                "agilidad": candidato["atributos"]["agilidad"],
                "habilidad_pasiva": candidato["habilidad_pasiva"],
                "vida_max": candidato.get("vida_max", VIDA_BASE),
                "vida_actual": candidato.get("vida_max", VIDA_BASE),
                "mana_max": candidato.get("mana_max", MANA_BASE),
                "mana_actual": candidato.get("mana_max", MANA_BASE),
                "hechizos_conocidos": list(candidato.get("hechizos_conocidos", [])),
            }
    raise ErrorCreacionPersonaje(
        f"No existe el personaje pregenerado '{personaje_pregenerado_id}' en esta historia."
    )


def construir_personalizado(
    historia_contenido: dict,
    nombre: str,
    atributos: dict[str, int],
    habilidad_pasiva: str,
) -> dict:
    if set(atributos.keys()) != set(ATRIBUTOS):
        raise ErrorCreacionPersonaje("Debes repartir puntos en los 4 atributos.")

    for atributo, valor in atributos.items():
        if not (PUNTOS_PERSONALIZADO_MIN <= valor <= PUNTOS_PERSONALIZADO_MAX):
            raise ErrorCreacionPersonaje(
                f"'{atributo}' debe estar entre {PUNTOS_PERSONALIZADO_MIN} y "
                f"{PUNTOS_PERSONALIZADO_MAX}."
            )

    if sum(atributos.values()) != PUNTOS_PERSONALIZADO_TOTAL:
        raise ErrorCreacionPersonaje(
            f"Debes repartir exactamente {PUNTOS_PERSONALIZADO_TOTAL} puntos en total."
        )

    habilidades_validas = set()
    for h in historia_contenido.get("habilidades_pasivas_personalizado", []):
        habilidades_validas.add(h["id"])
    if habilidades_validas and habilidad_pasiva not in habilidades_validas:
        raise ErrorCreacionPersonaje("Esa habilidad pasiva no está disponible para esta historia.")

    return {
        "nombre": nombre,
        "origen": "personalizado",
        "personaje_pregenerado_id": None,
        "trasfondo": None,
        "fuerza": atributos["fuerza"],
        "astucia": atributos["astucia"],
        "voluntad": atributos["voluntad"],
        "agilidad": atributos["agilidad"],
        "habilidad_pasiva": habilidad_pasiva,
        "vida_max": VIDA_BASE,
        "vida_actual": VIDA_BASE,
        "mana_max": MANA_BASE,
        "mana_actual": MANA_BASE,
        "hechizos_conocidos": [],
    }
