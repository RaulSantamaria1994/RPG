from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.engine.hechizos_base import hechizos_disponibles
from app.models.estado_sala import EstadoSala
from app.models.historia import Historia
from app.models.personaje import Personaje
from app.models.sala import Sala
from app.schemas.personaje import PersonajeOut
from app.schemas.sala import EstadoSalaOut, SalaCompletaOut, SalaCrear, SalaCreadaOut, SalaOut
from app.security import TokenPayload, crear_token, requerir_token
from app.utils import generar_codigo_sala

router = APIRouter(prefix="/salas", tags=["salas"])
settings = get_settings()


def _obtener_sala_por_codigo(codigo: str, db: Session) -> Sala:
    sala = db.query(Sala).filter(Sala.codigo == codigo.upper()).first()
    if not sala:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ninguna sala con ese código.")
    return sala


def _requerir_master_de_sala(sala: Sala, payload: TokenPayload) -> None:
    if payload.rol != "master" or payload.sala_id != str(sala.id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo el máster de esta sala puede hacer esto."
        )


@router.post("", response_model=SalaCreadaOut, status_code=status.HTTP_201_CREATED)
def crear_sala(payload: SalaCrear, db: Session = Depends(get_db)):
    historia = (
        db.query(Historia)
        .filter(Historia.historia_id == payload.historia_id, Historia.validada.is_(True))
        .order_by(Historia.version.desc())
        .first()
    )
    if not historia:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No hay ninguna versión validada de esa historia disponible.",
        )

    if payload.min_jugadores > payload.max_jugadores:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "min_jugadores no puede ser mayor que max_jugadores.",
        )
    if payload.max_jugadores > settings.sala_max_jugadores_duro:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"max_jugadores no puede superar {settings.sala_max_jugadores_duro}.",
        )

    codigo = generar_codigo_sala(settings.codigo_sala_longitud)
    while db.query(Sala).filter(Sala.codigo == codigo).first():
        codigo = generar_codigo_sala(settings.codigo_sala_longitud)

    master_token_placeholder = ""  # se sustituye tras conocer el id de la sala
    sala = Sala(
        codigo=codigo,
        nombre=payload.nombre,
        historia_id=historia.id,
        historia_version=historia.version,
        master_nombre=payload.master_nombre,
        master_token=master_token_placeholder,
        min_jugadores=payload.min_jugadores,
        max_jugadores=payload.max_jugadores,
        muerte_permanente=payload.muerte_permanente,
    )
    db.add(sala)
    db.flush()

    token = crear_token(sala.id, rol="master", nombre=payload.master_nombre)
    sala.master_token = token

    estado = EstadoSala(sala_id=sala.id, nodo_actual_id=historia.contenido["nodo_inicial"])
    db.add(estado)

    db.commit()
    db.refresh(sala)
    return SalaCreadaOut(sala=sala, master_token=token)


@router.get("/{codigo}", response_model=SalaOut)
def obtener_sala(codigo: str, db: Session = Depends(get_db)):
    return _obtener_sala_por_codigo(codigo, db)


@router.get("/{codigo}/estado", response_model=SalaCompletaOut)
def obtener_estado_sala(
    codigo: str,
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(requerir_token),
):
    """Estado completo para reconectar: nodo actual, flags, personajes."""
    sala = _obtener_sala_por_codigo(codigo, db)
    if payload.sala_id != str(sala.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ese token no pertenece a esta sala.")

    nodo_actual = sala.historia.contenido["nodos"][sala.estado_sala.nodo_actual_id]
    personajes = db.query(Personaje).filter(Personaje.sala_id == sala.id).all()
    return SalaCompletaOut(
        sala=sala,
        estado=sala.estado_sala,
        nodo_actual=nodo_actual,
        personajes=[PersonajeOut.model_validate(p) for p in personajes],
    )


@router.get("/{codigo}/pregenerados")
def listar_pregenerados_disponibles(codigo: str, db: Session = Depends(get_db)):
    sala = _obtener_sala_por_codigo(codigo, db)
    todos = sala.historia.contenido.get("personajes_pregenerados", [])
    tomados = {
        p.personaje_pregenerado_id
        for p in db.query(Personaje).filter(Personaje.sala_id == sala.id).all()
        if p.personaje_pregenerado_id
    }
    return [p for p in todos if p["id"] not in tomados]


@router.get("/{codigo}/habilidades-personalizado")
def listar_habilidades_personalizado(codigo: str, db: Session = Depends(get_db)):
    sala = _obtener_sala_por_codigo(codigo, db)
    return sala.historia.contenido.get("habilidades_pasivas_personalizado", [])


@router.get("/{codigo}/hechizos")
def listar_hechizos_disponibles(codigo: str, db: Session = Depends(get_db)):
    sala = _obtener_sala_por_codigo(codigo, db)
    return list(hechizos_disponibles(sala.historia.contenido).values())


@router.get("/{codigo}/nodos")
def listar_nodos_historia(
    codigo: str,
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(requerir_token),
):
    """Lista de todos los nodos de la historia, para que el máster pueda
    elegir a cuál saltar sin tener que escribir el id a mano."""
    sala = _obtener_sala_por_codigo(codigo, db)
    _requerir_master_de_sala(sala, payload)

    return [
        {
            "id": nodo_id,
            "tipo": nodo.get("tipo"),
            "texto": nodo.get("texto", ""),
            "es_final": nodo.get("es_final", False),
            "tipo_final": nodo.get("tipo_final"),
        }
        for nodo_id, nodo in sala.historia.contenido.get("nodos", {}).items()
    ]


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_sala(
    codigo: str,
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(requerir_token),
):
    sala = _obtener_sala_por_codigo(codigo, db)
    _requerir_master_de_sala(sala, payload)
    db.delete(sala)
    db.commit()


@router.post("/{codigo}/regenerar-codigo", response_model=SalaOut)
def regenerar_codigo_sala(
    codigo: str,
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(requerir_token),
):
    sala = _obtener_sala_por_codigo(codigo, db)
    _requerir_master_de_sala(sala, payload)

    nuevo_codigo = generar_codigo_sala(settings.codigo_sala_longitud)
    while db.query(Sala).filter(Sala.codigo == nuevo_codigo).first():
        nuevo_codigo = generar_codigo_sala(settings.codigo_sala_longitud)
    sala.codigo = nuevo_codigo
    db.commit()
    db.refresh(sala)
    return sala


@router.post("/{codigo}/cerrar", response_model=SalaOut)
def cerrar_sala(
    codigo: str,
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(requerir_token),
):
    sala = _obtener_sala_por_codigo(codigo, db)
    _requerir_master_de_sala(sala, payload)
    sala.estado = "cerrada"
    db.commit()
    db.refresh(sala)
    return sala
