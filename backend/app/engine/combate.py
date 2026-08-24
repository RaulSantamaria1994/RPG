"""Resolución de combate por rondas, sin mapa/grid: tiradas narrativas.

El estado de combate vive en `EstadoSala.combate` (JSON) con esta forma:

{
  "enemigos": [
    {"enemigo_id": "lobo_1", "nombre": "Lobo", "vida": 8, "vida_max": 8,
     "atributos": {"fuerza": 3, "agilidad": 2}, "ataques": [...], "derrotado": False}
  ],
  "orden_iniciativa": ["personaje:<id>", "enemigo:lobo_1", ...],
  "turno_index": 0,
  "ronda": 1,
  "terminado": False,
  "resultado": null  # "victoria" | "derrota" | "huida" | "negociacion"
}
"""

from app.engine.dice import resolver_tirada, tirar_d20
from app.models.personaje import Personaje


def iniciar_combate(nodo: dict, personajes: list[Personaje]) -> dict:
    enemigos = [
        {
            **enemigo,
            "vida": enemigo.get("vida"),
            "vida_max": enemigo.get("vida"),
            "derrotado": False,
        }
        for enemigo in nodo.get("enemigos", [])
    ]

    participantes: list[tuple[str, int]] = []
    for personaje in personajes:
        iniciativa = tirar_d20() + personaje.agilidad
        participantes.append((f"personaje:{personaje.id}", iniciativa))
    for enemigo in enemigos:
        iniciativa = tirar_d20() + enemigo.get("atributos", {}).get("agilidad", 0)
        participantes.append((f"enemigo:{enemigo['enemigo_id']}", iniciativa))

    participantes.sort(key=lambda p: p[1], reverse=True)

    return {
        "enemigos": enemigos,
        "orden_iniciativa": [p[0] for p in participantes],
        "iniciativa_valores": {p[0]: p[1] for p in participantes},
        "turno_index": 0,
        "ronda": 1,
        "terminado": False,
        "resultado": None,
        "dificultad_huida": nodo.get("dificultad_huida", 12),
        "dificultad_negociacion": nodo.get("dificultad_negociacion", 13),
    }


def enemigo_en_combate(combate: dict, enemigo_id: str) -> dict | None:
    return next((e for e in combate["enemigos"] if e["enemigo_id"] == enemigo_id), None)


def _enemigo(combate: dict, enemigo_id: str) -> dict:
    for enemigo in combate["enemigos"]:
        if enemigo["enemigo_id"] == enemigo_id:
            return enemigo
    raise ValueError(f"Enemigo '{enemigo_id}' no está en este combate.")


def resolver_ataque_jugador(
    combate: dict, personaje: Personaje, enemigo_id: str, modificador_ataque: int
) -> dict:
    """Tirada opuesta: ataque del jugador vs defensa del enemigo."""
    enemigo = _enemigo(combate, enemigo_id)
    defensa = enemigo.get("atributos", {}).get("defensa", 10)

    resultado = resolver_tirada(modificador=modificador_ataque, dificultad=defensa)

    dano_aplicado = 0
    if resultado.exito:
        dano_aplicado = _dano_base(personaje)
        enemigo["vida"] = max(0, enemigo["vida"] - dano_aplicado)
        if enemigo["vida"] == 0:
            enemigo["derrotado"] = True

    return {
        "tirada": resultado.to_dict(),
        "dano_aplicado": dano_aplicado,
        "enemigo_id": enemigo_id,
        "enemigo_derrotado": enemigo["derrotado"],
    }


def _dano_base(personaje: Personaje) -> int:
    return max(1, personaje.fuerza // 2 + 2)


def resolver_ataque_enemigo(combate: dict, enemigo_id: str, personaje: Personaje) -> dict:
    enemigo = _enemigo(combate, enemigo_id)
    ataques = enemigo.get("ataques") or [{"nombre": "Ataque", "dano": 2, "modificador": 2}]
    ataque = ataques[0]

    defensa_jugador = 10 + personaje.agilidad
    resultado = resolver_tirada(
        modificador=ataque.get("modificador", 0), dificultad=defensa_jugador
    )

    dano_aplicado = 0
    if resultado.exito:
        dano_aplicado = ataque.get("dano", 2)
        personaje.vida_actual = max(0, personaje.vida_actual - dano_aplicado)
        if personaje.vida_actual == 0:
            personaje.estado = "inconsciente"

    return {
        "tirada": resultado.to_dict(),
        "dano_aplicado": dano_aplicado,
        "personaje_id": str(personaje.id),
        "personaje_inconsciente": personaje.vida_actual == 0,
    }


def avanzar_turno(combate: dict) -> None:
    combate["turno_index"] += 1
    if combate["turno_index"] >= len(combate["orden_iniciativa"]):
        combate["turno_index"] = 0
        combate["ronda"] += 1


def turno_actual(combate: dict) -> str:
    return combate["orden_iniciativa"][combate["turno_index"]]


def evaluar_fin_combate(combate: dict) -> str | None:
    """Devuelve 'victoria' si todos los enemigos están derrotados, o None."""
    if combate["enemigos"] and all(e["derrotado"] for e in combate["enemigos"]):
        combate["terminado"] = True
        combate["resultado"] = "victoria"
        return "victoria"
    return None
