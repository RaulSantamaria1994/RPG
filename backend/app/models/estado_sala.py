import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import JSONVariant


class EstadoSala(Base):
    """Estado narrativo persistido de una sala: dónde está, qué flags tiene,
    qué palabras clave ya se agotaron, inventario de grupo y estado de combate.
    """

    __tablename__ = "estado_sala"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sala_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("salas.id"), nullable=False, unique=True
    )

    nodo_actual_id: Mapped[str] = mapped_column(String(60), nullable=False)

    flags: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    palabras_clave_usadas: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    inventario_grupo: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)

    # exploracion | combate
    fase: Mapped[str] = mapped_column(String(20), nullable=False, default="exploracion")
    combate: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    finalizada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tipo_final: Mapped[str | None] = mapped_column(String(40), nullable=True)

    sala = relationship("Sala", back_populates="estado_sala")
