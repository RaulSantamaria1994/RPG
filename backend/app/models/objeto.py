import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import JSONVariant


class Objeto(Base):
    """Catálogo/instancia de objeto obtenido durante la partida. El inventario
    de personaje y de grupo referencia estos objetos por `objeto_id` (string
    del JSON de la historia) o guarda instancias sueltas aquí para trazabilidad.
    """

    __tablename__ = "objetos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sala_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salas.id"), nullable=False)

    objeto_id: Mapped[str] = mapped_column(String(60), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    consumible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    efecto: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    # personaje | grupo
    ubicacion: Mapped[str] = mapped_column(String(20), nullable=False, default="grupo")
    personaje_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("personajes.id"), nullable=True
    )
