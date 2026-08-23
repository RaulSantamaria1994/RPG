"""Sistema de dados: d20 + modificador de atributo contra una dificultad."""

import secrets
from dataclasses import dataclass


@dataclass
class ResultadoTirada:
    dado: int
    modificador: int
    total: int
    dificultad: int
    exito: bool
    ventaja: bool = False
    desventaja: bool = False
    dado_descartado: int | None = None

    def to_dict(self) -> dict:
        return {
            "dado": self.dado,
            "modificador": self.modificador,
            "total": self.total,
            "dificultad": self.dificultad,
            "exito": self.exito,
            "ventaja": self.ventaja,
            "desventaja": self.desventaja,
            "dado_descartado": self.dado_descartado,
        }


def tirar_d20() -> int:
    """Tirada segura de un d20 (1-20), no predecible por el cliente."""
    return secrets.randbelow(20) + 1


def resolver_tirada(
    modificador: int,
    dificultad: int,
    ventaja: bool = False,
    desventaja: bool = False,
) -> ResultadoTirada:
    """Resuelve una tirada d20 + modificador contra una dificultad.

    Ventaja y desventaja se cancelan si ambas están presentes (regla D&D
    estándar), evitando que se puedan combinar para anularse sin más.
    """
    if ventaja and desventaja:
        ventaja = desventaja = False

    dado_descartado = None
    if ventaja or desventaja:
        d1, d2 = tirar_d20(), tirar_d20()
        if ventaja:
            dado, dado_descartado = max(d1, d2), min(d1, d2)
        else:
            dado, dado_descartado = min(d1, d2), max(d1, d2)
    else:
        dado = tirar_d20()

    total = dado + modificador
    exito = total >= dificultad

    return ResultadoTirada(
        dado=dado,
        modificador=modificador,
        total=total,
        dificultad=dificultad,
        exito=exito,
        ventaja=ventaja,
        desventaja=desventaja,
        dado_descartado=dado_descartado,
    )


def resolver_tirada_opuesta(modificador_jugador: int, modificador_rival: int) -> dict:
    """Tirada de un jugador contra la de un NPC/enemigo (persuasión vs recelo,
    fuerza vs fuerza), en vez de contra una dificultad fija. Un empate lo
    gana quien se opone al cambio (el rival), como es convención habitual.
    """
    tirada_jugador = resolver_tirada(modificador_jugador, dificultad=0)
    tirada_rival = resolver_tirada(modificador_rival, dificultad=0)
    exito = tirada_jugador.total > tirada_rival.total
    return {
        "jugador": {**tirada_jugador.to_dict(), "exito": exito},
        "rival": {**tirada_rival.to_dict(), "exito": not exito},
        "exito": exito,
    }
