"""Combate PbtA: se resuelve con las mismas movidas y las mismas bandas que
cualquier otra tirada (ver docs/motor_pbta_plan.md, sección 6). Los
enemigos no tiran: solo tienen vida y un daño fijo que infligen al
contraatacar, determinista según la banda de la movida del jugador — no
hay un paso de "reacción del enemigo" aparte, va dentro de la propia
resolución. Tampoco hay iniciativa de d20: el orden de turno es
simplemente el de llegada.

El estado de combate vive en `EstadoSala.combate` (JSON) con esta forma:

{
  "enemigos": [
    {"enemigo_id": "urbano", "nombre": "Urbano", "vida": 16, "vida_max": 16,
     "dano": 6, "derrotado": False}
  ],
  "orden_iniciativa": ["personaje:<id>", ...],
  "turno_index": 0,
  "ronda": 1,
  "terminado": False,
  "resultado": None  # "victoria" | "derrota" | "huida"
}

Los hechizos quedan fuera de este combate por ahora (ver
docs/motor_pbta_plan.md, sección 7: se dejan para más adelante, sin
rediseñar su integración con el combate reactivo que tenían antes).
"""

import secrets

from app.engine.dice import Banda, resolver_tirada
from app.engine.movidas import modificador_de
from app.engine.resolver import aplicar_dano
from app.models.personaje import Personaje


def iniciar_combate(nodo: dict, personajes: list[Personaje]) -> dict:
    enemigos = []
    for enemigo in nodo.get("enemigos", []):
        copia = dict(enemigo)
        copia["vida_max"] = enemigo.get("vida")
        copia["derrotado"] = False
        enemigos.append(copia)

    orden_iniciativa = [f"personaje:{p.id}" for p in personajes]

    return {
        "enemigos": enemigos,
        "orden_iniciativa": orden_iniciativa,
        "turno_index": 0,
        "ronda": 1,
        "terminado": False,
        "resultado": None,
    }


def enemigo_en_combate(combate: dict, enemigo_id: str) -> dict | None:
    for e in combate["enemigos"]:
        if e["enemigo_id"] == enemigo_id:
            return e
    return None


def elegir_enemigo_reactivo(combate: dict) -> dict | None:
    """Un enemigo vivo al azar, para cuando hace falta que "alguien"
    responda sin que la acción apuntara a uno en concreto (p. ej. al
    fallar un intento de huida)."""
    vivos = [e for e in combate["enemigos"] if not e["derrotado"]]
    if not vivos:
        return None
    return vivos[secrets.randbelow(len(vivos))]


def _dano_arma(personaje: Personaje) -> int:
    return 1 + (personaje.arma_equipada or {}).get("bono_dano", 0)


def resolver_golpear(
    combate: dict, personaje: Personaje, enemigo_id: str, muerte_permanente: bool = False
) -> dict:
    """10+: golpeas limpio, el enemigo no responde. 7-9: golpeas, pero el
    enemigo contraataca. 6-: no golpeas, y el enemigo contraataca igual."""
    enemigo = enemigo_en_combate(combate, enemigo_id)
    resultado = resolver_tirada(modificador_de(personaje, "fuerza"))

    dano_a_enemigo = 0
    dano_recibido = 0
    if resultado.banda in (Banda.EXITO, Banda.EXITO_CON_COSTE):
        dano_a_enemigo = _dano_arma(personaje)
        enemigo["vida"] = max(0, enemigo["vida"] - dano_a_enemigo)
        if enemigo["vida"] == 0:
            enemigo["derrotado"] = True
    if resultado.banda in (Banda.EXITO_CON_COSTE, Banda.FALLO):
        dano_recibido = aplicar_dano(personaje, enemigo.get("dano", 2), muerte_permanente)

    return {
        "tirada": resultado.to_dict(),
        "enemigo_id": enemigo_id,
        "dano_a_enemigo": dano_a_enemigo,
        "dano_recibido": dano_recibido,
        "enemigo_derrotado": enemigo["derrotado"],
    }


def resolver_proteger(
    combate: dict,
    protector: Personaje,
    protegido: Personaje,
    enemigo_id: str,
    muerte_permanente: bool = False,
) -> dict:
    """10+: nadie recibe daño, controlas la situación. 7-9: el golpe
    destinado al protegido te lo llevas tú. 6-: fallas al interponerte, el
    golpe llega igualmente a quien protegías."""
    enemigo = enemigo_en_combate(combate, enemigo_id)
    resultado = resolver_tirada(modificador_de(protector, "fuerza"))

    dano_protector = 0
    dano_protegido = 0
    if resultado.banda == Banda.EXITO_CON_COSTE:
        dano_protector = aplicar_dano(protector, enemigo.get("dano", 2), muerte_permanente)
    elif resultado.banda == Banda.FALLO:
        dano_protegido = aplicar_dano(protegido, enemigo.get("dano", 2), muerte_permanente)

    return {
        "tirada": resultado.to_dict(),
        "enemigo_id": enemigo_id,
        "protegido_id": str(protegido.id),
        "dano_protector": dano_protector,
        "dano_protegido": dano_protegido,
    }


def resolver_escabullirse(combate: dict, personaje: Personaje, muerte_permanente: bool = False) -> dict:
    """10+: huyes limpio. 7-9: huyes, pero te alcanzan antes de salir. 6-:
    no consigues huir, y te alcanzan igual."""
    resultado = resolver_tirada(modificador_de(personaje, "agilidad"))

    huido = resultado.banda in (Banda.EXITO, Banda.EXITO_CON_COSTE)
    dano_recibido = 0
    if resultado.banda in (Banda.EXITO_CON_COSTE, Banda.FALLO):
        enemigo = elegir_enemigo_reactivo(combate)
        if enemigo is not None:
            dano_recibido = aplicar_dano(personaje, enemigo.get("dano", 2), muerte_permanente)

    return {"tirada": resultado.to_dict(), "huido": huido, "dano_recibido": dano_recibido}


def resolver_actuar_bajo_presion(
    combate: dict, personaje: Personaje, muerte_permanente: bool = False
) -> dict:
    """Cajón de sastre para cualquier otra acción arriesgada en pleno
    combate (usar algo del entorno, improvisar) que no sea atacar,
    proteger o huir. 7-9: sale bien, pero con un pequeño coste."""
    resultado = resolver_tirada(modificador_de(personaje, "voluntad"))
    dano_recibido = 0
    if resultado.banda == Banda.EXITO_CON_COSTE:
        dano_recibido = aplicar_dano(personaje, 1, muerte_permanente)
    return {"tirada": resultado.to_dict(), "dano_recibido": dano_recibido}


def avanzar_turno(combate: dict) -> None:
    combate["turno_index"] += 1
    if combate["turno_index"] >= len(combate["orden_iniciativa"]):
        combate["turno_index"] = 0
        combate["ronda"] += 1


def evaluar_fin_combate(combate: dict) -> str | None:
    """Devuelve 'victoria' si todos los enemigos están derrotados, o None."""
    if not combate["enemigos"]:
        return None
    if all(e["derrotado"] for e in combate["enemigos"]):
        combate["terminado"] = True
        combate["resultado"] = "victoria"
        return "victoria"
    return None
