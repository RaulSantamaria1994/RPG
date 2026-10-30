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

    # Barra de daño PbtA: fija en 7 para todos los personajes (ver
    # docs/motor_pbta_plan.md, sección 3) — ya no varía por personaje ni
    # por historia, pero se deja como columna normal en vez de una
    # constante de código para no tener que tocar cada sitio que ya lee
    # personaje.vida_max.
    vida_max: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    vida_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    # Puntos de Suerte (ver docs/motor_pbta_plan.md, sección 4): 7 al
    # crear el personaje, no se recuperan solos.
    puntos_suerte_max: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    puntos_suerte_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    mana_max: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    mana_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    inventario: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    hechizos_conocidos: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    rasgos: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)

    # Objeto equipado del inventario común (categoria "arma"/"armadura"/
    # "grimorio" de ObjetoInventario), o None si no lleva nada en esa
    # ranura.
    arma_equipada: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True, default=None)
    armadura_equipada: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True, default=None)
    hechizo_equipado: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True, default=None)

    # activo | inconsciente | muerto
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")

    es_master: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    sala = relationship("Sala", back_populates="personajes")
