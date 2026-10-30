"""Sistema de dados: 2d6 + modificador de característica, leído en tres
bandas fijas, iguales para toda tirada del juego (ver docs/motor_pbta_plan.md):

  - 10+          -> éxito limpio
  - 7, 8 o 9     -> éxito con coste
  - 6 o menos    -> fallo

Sustituye al d20 + dificultad por nodo: ya no hay un número de dificultad
que inventar en cada palabra clave, los umbrales son siempre los mismos.
"""

import secrets
from dataclasses import dataclass
from enum import Enum


class Banda(str, Enum):
    EXITO = "exito"
    EXITO_CON_COSTE = "exito_con_coste"
    FALLO = "fallo"


@dataclass
class ResultadoTirada:
    dados: tuple[int, int]
    modificador: int
    total: int
    banda: Banda

    @property
    def exito(self) -> bool:
        """True en 10+ y en 7-9 (el 7-9 avanza la historia igual que el
        10+, solo que con un coste añadido) — False únicamente en 6-."""
        return self.banda != Banda.FALLO

    def to_dict(self) -> dict:
        return {
            "dados": list(self.dados),
            "modificador": self.modificador,
            "total": self.total,
            "banda": self.banda.value,
            "exito": self.exito,
        }


def tirar_d6() -> int:
    """Tirada segura de un d6 (1-6), no predecible por el cliente."""
    return secrets.randbelow(6) + 1


def banda_de(total: int) -> Banda:
    if total >= 10:
        return Banda.EXITO
    if total >= 7:
        return Banda.EXITO_CON_COSTE
    return Banda.FALLO


def resolver_tirada(modificador: int) -> ResultadoTirada:
    """Tira 2d6, suma el modificador y devuelve el resultado con su banda."""
    d1, d2 = tirar_d6(), tirar_d6()
    total = d1 + d2 + modificador
    return ResultadoTirada(dados=(d1, d2), modificador=modificador, total=total, banda=banda_de(total))


# ---------------------------------------------------------------------------
# Compatibilidad temporal con el combate viejo (d20 + dificultad), que
# todavía no se ha rediseñado en PbtA — ver docs/motor_pbta_plan.md, Fase 2.
# Solo lo usan app/engine/combate.py y app/websockets/handlers/combate.py;
# se retira entero en cuanto se haga esa fase, junto con esos dos módulos.
# ---------------------------------------------------------------------------

from dataclasses import dataclass as _dataclass  # noqa: E402


def tirar_d20() -> int:
    return secrets.randbelow(20) + 1


@_dataclass
class ResultadoTiradaD20:
    dado: int
    modificador: int
    total: int
    dificultad: int
    exito: bool

    def to_dict(self) -> dict:
        return {
            "dado": self.dado,
            "modificador": self.modificador,
            "total": self.total,
            "dificultad": self.dificultad,
            "exito": self.exito,
        }


def resolver_tirada_legacy_d20(modificador: int, dificultad: int) -> ResultadoTiradaD20:
    dado = tirar_d20()
    total = dado + modificador
    return ResultadoTiradaD20(
        dado=dado, modificador=modificador, total=total, dificultad=dificultad, exito=total >= dificultad
    )
