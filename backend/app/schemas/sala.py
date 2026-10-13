import uuid

from pydantic import BaseModel, ConfigDict, Field


class SalaCrear(BaseModel):
    master_nombre: str = Field(min_length=1, max_length=60)
    historia_id: str
    nombre: str | None = None
    min_jugadores: int = Field(default=2, ge=1)
    max_jugadores: int = Field(default=6, le=6)
    muerte_permanente: bool = False


class SalaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str | None
    historia_id: uuid.UUID
    historia_version: int
    min_jugadores: int
    max_jugadores: int
    estado: str
    muerte_permanente: bool


class SalaCreadaOut(BaseModel):
    sala: SalaOut
    master_token: str


class EstadoSalaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nodo_actual_id: str
    flags: dict
    palabras_clave_usadas: list
    inventario_grupo: list
    fase: str
    combate: dict | None
    finalizada: bool
    tipo_final: str | None


class SalaCompletaOut(BaseModel):
    sala: SalaOut
    estado: EstadoSalaOut
    nodo_actual: dict
    personajes: list["PersonajeOut"]


from app.schemas.personaje import PersonajeOut  # noqa: E402

SalaCompletaOut.model_rebuild()
