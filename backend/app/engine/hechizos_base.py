"""Lista base de hechizos del motor, reutilizable entre historias.

Una historia puede añadir o sobreescribir hechizos propios en su campo
`hechizos` del JSON; `resolver_hechizos_disponibles` combina ambas listas.
"""

HECHIZOS_BASE: dict[str, dict] = {
    "luz_fantasma": {
        "hechizo_id": "luz_fantasma",
        "nombre": "Luz fantasma",
        "categoria": "utilidad",
        "coste_mana": 2,
        "dificultad": 10,
        "descripcion": "Ilumina un área o revela texto oculto.",
        "efecto": "revela_palabra_clave_oculta",
    },
    "dardo_arcano": {
        "hechizo_id": "dardo_arcano",
        "nombre": "Dardo arcano",
        "categoria": "combate",
        "coste_mana": 3,
        "dificultad": 11,
        "descripcion": "Un proyectil de energía mágica que golpea a un enemigo.",
        "efecto": "dano_directo",
    },
    "mano_calmada": {
        "hechizo_id": "mano_calmada",
        "nombre": "Mano calmada",
        "categoria": "social",
        "coste_mana": 2,
        "dificultad": 12,
        "descripcion": "Serena a un NPC alterado u hostil.",
        "efecto": "calmar_npc",
    },
    "toque_curativo": {
        "hechizo_id": "toque_curativo",
        "nombre": "Toque curativo",
        "categoria": "curacion",
        "coste_mana": 4,
        "dificultad": 10,
        "descripcion": "Restaura vida o maná a otro personaje.",
        "efecto": "restaura_vida_o_mana",
    },
}


def hechizos_disponibles(contenido_historia: dict) -> dict[str, dict]:
    combinados = dict(HECHIZOS_BASE)
    for hechizo in contenido_historia.get("hechizos", []) or []:
        combinados[hechizo["hechizo_id"]] = hechizo
    return combinados
