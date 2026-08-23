"""Formas de los mensajes intercambiados por el WebSocket de sala.

El protocolo es JSON con un campo `tipo` que discrimina la acción. No se usa
`BaseModel` estricto para los mensajes entrantes (se valida a mano en el
handler) para poder dar mensajes de error claros por WebSocket en vez de
cerrar la conexión ante un payload inválido.
"""

from pydantic import BaseModel


class MensajeSalida(BaseModel):
    tipo: str
    datos: dict

    def to_json(self) -> dict:
        return {"tipo": self.tipo, "datos": self.datos}
