import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import JSONVariant


class HistorialDecision(Base):
    """Log de cada decisión/tirada resuelta en una sala. Es la base tanto
    del panel del máster como de la recapitulación al reabrir una sala.
    """

    __tablename__ = "historial_decisiones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sala_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salas.id"), nullable=False)
    personaje_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("personajes.id"), nullable=True
    )

    nodo_id: Mapped[str] = mapped_column(String(60), nullable=False)
    palabra_clave_texto: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo_interaccion: Mapped[str | None] = mapped_column(String(40), nullable=True)

    resultado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tirada: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    nodo_destino_id: Mapped[str | None] = mapped_column(String(60), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sala = relationship("Sala", back_populates="historial")
