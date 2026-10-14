import uuid

from pydantic import BaseModel, ConfigDict, Field


class PersonajeCrearPregenerado(BaseModel):
    jugador_nombre: str = Field(min_length=1, max_length=60)
    personaje_pregenerado_id: str


class PersonajeCrearPersonalizado(BaseModel):
    jugador_nombre: str = Field(min_length=1, max_length=60)
    nombre: str = Field(min_length=1, max_length=80)
    atributos: dict[str, int]
    habilidad_pasiva: str


class PersonajeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sala_id: uuid.UUID
    jugador_nombre: str
    nombre: str
    origen: str
    trasfondo: str | None
    fuerza: int
    astucia: int
    voluntad: int
    agilidad: int
    habilidad_pasiva: str
    vida_max: int
    vida_actual: int
    mana_max: int
    mana_actual: int
    inventario: list
    hechizos_conocidos: list
    rasgos: list
    arma_equipada: dict | None
    hechizo_equipado: dict | None
    estado: str
    es_master: bool


class PersonajeCreadoOut(BaseModel):
    personaje: PersonajeOut
    token: str
