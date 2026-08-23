import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import JSONVariant


class Personaje(Base):
    """Ficha de un jugador dentro de una sala concreta."""

    __tablename__ = "personajes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sala_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salas.id"), nullable=False)

    jugador_nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    jugador_token: Mapped[str] = mapped_column(Text, nullable=False)

    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    # pregenerado | personalizado
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    personaje_pregenerado_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    trasfondo: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    fuerza: Mapped[int] = mapped_column(Integer, nullable=False)
    astucia: Mapped[int] = mapped_column(Integer, nullable=False)
    voluntad: Mapped[int] = mapped_column(Integer, nullable=False)
    agilidad: Mapped[int] = mapped_column(Integer, nullable=False)

    habilidad_pasiva: Mapped[str] = mapped_column(String(80), nullable=False)

    vida_max: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    vida_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    mana_max: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    mana_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    inventario: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    hechizos_conocidos: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    rasgos: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)

    # activo | inconsciente | muerto
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")

    es_master: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    sala = relationship("Sala", back_populates="personajes")
