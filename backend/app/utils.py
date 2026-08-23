import secrets
import string

_ALFABETO_CODIGO = string.ascii_uppercase + string.digits
# Excluye caracteres fácilmente confundibles (0/O, 1/I) para que el código
# sea fácil de dictar/transcribir entre jugadores.
_ALFABETO_CODIGO = "".join(c for c in _ALFABETO_CODIGO if c not in "01OI")


def generar_codigo_sala(longitud: int = 6) -> str:
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(longitud))
