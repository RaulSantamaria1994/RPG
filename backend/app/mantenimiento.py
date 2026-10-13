"""Limpieza de salas abandonadas.

Una partida puede quedar abierta días sin que nadie vuelva: el máster no
cierra la sala explícitamente, simplemente nadie reconecta. `Sala.
ultima_actividad_en` ya se actualiza con cada mensaje WS (ver
`app.websockets.sala_ws.sala_websocket`); aquí solo se usa ese dato para
decidir qué salas llevan demasiado tiempo quietas y borrarlas, junto con
todo lo que cuelga de ellas por cascada (estado, personajes, inventario).
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.sala import Sala

settings = get_settings()


def limpiar_salas_expiradas(db: Session, ahora: datetime | None = None) -> int:
    """Borra las salas sin actividad desde hace más de
    `settings.sala_expiracion_dias`. Devuelve cuántas se borraron."""
    ahora = ahora or datetime.now(timezone.utc)
    limite = ahora - timedelta(days=settings.sala_expiracion_dias)

    expiradas = db.query(Sala).filter(Sala.ultima_actividad_en < limite).all()
    for sala in expiradas:
        db.delete(sala)
    db.commit()
    return len(expiradas)
