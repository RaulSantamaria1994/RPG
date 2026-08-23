import uuid

from pydantic import BaseModel, ConfigDict


class HistoriaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    historia_id: str
    titulo: str
    version: int
    validada: bool


class HistoriaDetalle(HistoriaResumen):
    contenido: dict
    errores_validacion: list[str] | None = None


class HistoriaCrear(BaseModel):
    contenido: dict


class HistoriaValidarOut(BaseModel):
    valida: bool
    errores: list[str]
