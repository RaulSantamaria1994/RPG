import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import JSONVariant


class Historia(Base):
    """Una versión concreta de una historia. El contenido completo (nodos,
    palabras clave, personajes pregenerados, hechizos) vive en `contenido`.
    """

    __tablename__ = "historias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    historia_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    contenido: Mapped[dict] = mapped_column(JSONVariant, nullable=False)

    validada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    errores_validacion: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)

    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("historia_id", "version", name="uq_historia_version"),)
