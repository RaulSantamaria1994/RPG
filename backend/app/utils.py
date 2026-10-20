import secrets
import string

_ALFABETO_CODIGO = string.ascii_uppercase + string.digits
# Excluye caracteres fácilmente confundibles (0/O, 1/I) para que el código
# sea fácil de dictar/transcribir entre jugadores.
_alfabeto_filtrado = ""
for c in _ALFABETO_CODIGO:
    if c not in "01OI":
        _alfabeto_filtrado += c
_ALFABETO_CODIGO = _alfabeto_filtrado


def generar_codigo_sala(longitud: int = 6) -> str:
    codigo = ""
    for _ in range(longitud):
        codigo += secrets.choice(_ALFABETO_CODIGO)
    return codigo
