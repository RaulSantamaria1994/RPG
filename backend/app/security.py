"""JWT ligero: el máster y cada jugador reciben un token al crear sala /
crear personaje que identifica su rol y, si aplica, su personaje. No hay
contraseñas: la posesión del código de sala (y del token una vez unido) es
la barrera de acceso, como describe el spec de seguridad de sala.
"""

import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()


class TokenPayload(BaseModel):
    sala_id: str
    rol: Literal["master", "jugador"]
    personaje_id: str | None = None
    nombre: str


def crear_token(sala_id: uuid.UUID, rol: str, nombre: str, personaje_id: uuid.UUID | None = None) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sala_id": str(sala_id),
        "rol": rol,
        "nombre": nombre,
        "personaje_id": str(personaje_id) if personaje_id else None,
        "exp": expira,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> TokenPayload:
    try:
        datos = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o caducado."
        ) from exc
    return TokenPayload(
        sala_id=datos["sala_id"],
        rol=datos["rol"],
        personaje_id=datos.get("personaje_id"),
        nombre=datos["nombre"],
    )


def requerir_token(authorization: str | None = Header(default=None)) -> TokenPayload:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta el token de sesión."
        )
    return decodificar_token(authorization.split(" ", 1)[1])


def requerir_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Guarda los endpoints de administración de contenido (subir/publicar
    historias). No es un JWT de sala: es un token fijo de administrador,
    configurado por variable de entorno (`admin_token`). Si no está
    configurado, estos endpoints quedan cerrados en cualquier entorno."""
    if not settings.admin_token or not x_admin_token or not hmac.compare_digest(
        x_admin_token, settings.admin_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de administrador inválido."
        )
