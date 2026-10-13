import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Sala(Base):
    """Una partida en curso. Vive anclada a una versión concreta de Historia."""

    __tablename__ = "salas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(6), unique=True, index=True, nullable=False)

    nombre: Mapped[str | None] = mapped_column(String(120), nullable=True)

    historia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("historias.id"), nullable=False)
    historia_version: Mapped[int] = mapped_column(Integer, nullable=False)

    master_nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    master_token: Mapped[str] = mapped_column(Text, nullable=False)

    min_jugadores: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_jugadores: Mapped[int] = mapped_column(Integer, nullable=False, default=6)

    # activa | pausada | cerrada
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")

    muerte_permanente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ultima_actividad_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    historia = relationship("Historia")
    estado_sala = relationship(
        "EstadoSala", back_populates="sala", uselist=False, cascade="all, delete-orphan"
    )
    personajes = relationship(
        "Personaje", back_populates="sala", cascade="all, delete-orphan"
    )
