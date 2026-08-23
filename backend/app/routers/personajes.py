from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.engine.personajes import ErrorCreacionPersonaje, construir_personalizado, construir_pregenerado
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.schemas.personaje import (
    PersonajeCreadoOut,
    PersonajeCrearPersonalizado,
    PersonajeCrearPregenerado,
    PersonajeOut,
)
from app.security import TokenPayload, crear_token, requerir_token

router = APIRouter(prefix="/salas/{codigo}/personajes", tags=["personajes"])


def _obtener_sala(codigo: str, db: Session) -> Sala:
    sala = db.query(Sala).filter(Sala.codigo == codigo.upper()).first()
    if not sala:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ninguna sala con ese código.")
    if sala.estado != "activa":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta sala no admite nuevos jugadores.")
    return sala


def _verificar_capacidad(sala: Sala, db: Session) -> None:
    actuales = db.query(Personaje).filter(Personaje.sala_id == sala.id).count()
    if actuales >= sala.max_jugadores:
        raise HTTPException(status.HTTP_409_CONFLICT, "La sala ya está completa.")


def _crear_y_guardar(sala: Sala, jugador_nombre: str, datos: dict, db: Session) -> PersonajeCreadoOut:
    personaje = Personaje(sala_id=sala.id, jugador_nombre=jugador_nombre, jugador_token="", **datos)
    db.add(personaje)
    db.flush()

    token = crear_token(sala.id, rol="jugador", nombre=jugador_nombre, personaje_id=personaje.id)
    personaje.jugador_token = token

    db.commit()
    db.refresh(personaje)
    return PersonajeCreadoOut(personaje=PersonajeOut.model_validate(personaje), token=token)


@router.get("", response_model=list[PersonajeOut])
def listar_personajes(codigo: str, db: Session = Depends(get_db)):
    sala = db.query(Sala).filter(Sala.codigo == codigo.upper()).first()
    if not sala:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ninguna sala con ese código.")
    return db.query(Personaje).filter(Personaje.sala_id == sala.id).all()


@router.post("/pregenerado", response_model=PersonajeCreadoOut, status_code=status.HTTP_201_CREATED)
def crear_personaje_pregenerado(
    codigo: str, payload: PersonajeCrearPregenerado, db: Session = Depends(get_db)
):
    sala = _obtener_sala(codigo, db)
    _verificar_capacidad(sala, db)

    ya_tomado = (
        db.query(Personaje)
        .filter(
            Personaje.sala_id == sala.id,
            Personaje.personaje_pregenerado_id == payload.personaje_pregenerado_id,
        )
        .first()
    )
    if ya_tomado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese personaje pregenerado ya está en juego.")

    try:
        datos = construir_pregenerado(sala.historia.contenido, payload.personaje_pregenerado_id)
    except ErrorCreacionPersonaje as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return _crear_y_guardar(sala, payload.jugador_nombre, datos, db)


@router.post("/personalizado", response_model=PersonajeCreadoOut, status_code=status.HTTP_201_CREATED)
def crear_personaje_personalizado(
    codigo: str, payload: PersonajeCrearPersonalizado, db: Session = Depends(get_db)
):
    sala = _obtener_sala(codigo, db)
    _verificar_capacidad(sala, db)

    try:
        datos = construir_personalizado(
            sala.historia.contenido, payload.nombre, payload.atributos, payload.habilidad_pasiva
        )
    except ErrorCreacionPersonaje as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return _crear_y_guardar(sala, payload.jugador_nombre, datos, db)


@router.post("/{personaje_id}/objetos", response_model=PersonajeOut)
def override_inventario_personaje(
    codigo: str,
    personaje_id: str,
    objeto: dict,
    quitar: bool = False,
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(requerir_token),
):
    """Override manual del máster: añade o quita un objeto a un personaje a mano."""
    sala = db.query(Sala).filter(Sala.codigo == codigo.upper()).first()
    if not sala:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ninguna sala con ese código.")
    if payload.rol != "master" or payload.sala_id != str(sala.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el máster puede editar inventarios.")

    personaje = (
        db.query(Personaje)
        .filter(Personaje.id == personaje_id, Personaje.sala_id == sala.id)
        .first()
    )
    if not personaje:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Personaje no encontrado en esta sala.")

    inventario = list(personaje.inventario or [])
    if quitar:
        inventario = [o for o in inventario if o.get("objeto_id") != objeto.get("objeto_id")]
    else:
        inventario.append(objeto)
    personaje.inventario = inventario
    flag_modified(personaje, "inventario")

    db.commit()
    db.refresh(personaje)
    return personaje
