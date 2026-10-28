from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.validator import validar_historia
from app.models.historia import Historia
from app.schemas.historia import (
    HistoriaCrear,
    HistoriaDetalle,
    HistoriaResumen,
    HistoriaValidarOut,
)
from app.security import requerir_admin

router = APIRouter(prefix="/historias", tags=["historias"])


@router.get("", response_model=list[HistoriaResumen])
def listar_historias(db: Session = Depends(get_db)):
    """Última versión PUBLICADA de cada historia (para el selector del
    máster). Una historia puede estar validada y aun así no aparecer aquí
    si todavía no se ha publicado."""
    subq = (
        db.query(Historia.historia_id, func.max(Historia.version).label("max_version"))
        .filter(Historia.publicada.is_(True))
        .group_by(Historia.historia_id)
        .subquery()
    )
    historias = (
        db.query(Historia)
        .join(
            subq,
            (Historia.historia_id == subq.c.historia_id)
            & (Historia.version == subq.c.max_version),
        )
        .order_by(Historia.titulo)
        .all()
    )
    return historias


@router.get("/{historia_id}", response_model=HistoriaDetalle)
def obtener_historia(historia_id: str, db: Session = Depends(get_db)):
    historia = (
        db.query(Historia)
        .filter(Historia.historia_id == historia_id)
        .order_by(Historia.version.desc())
        .first()
    )
    if not historia:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Historia no encontrada.")
    return historia


@router.post("/validar", response_model=HistoriaValidarOut)
def validar_contenido_historia(payload: HistoriaCrear):
    """Valida un JSON de historia sin persistirlo, para revisarlo antes de subirlo."""
    resultado = validar_historia(payload.contenido)
    return HistoriaValidarOut(valida=resultado.valida, errores=resultado.errores)


@router.post(
    "",
    response_model=HistoriaDetalle,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requerir_admin)],
)
def crear_historia(payload: HistoriaCrear, db: Session = Depends(get_db)):
    """Sube una nueva historia o una nueva versión de una existente.

    Si `historia_id` ya existe, se crea automáticamente la siguiente versión
    para no romper las salas en curso ancladas a la versión anterior.
    Entra sin publicar (`publicada=False`): no aparece en el selector del
    máster hasta llamar a `POST /historias/{historia_id}/publicar`, pero ya
    se puede probar creando una sala directamente contra su `historia_id`
    si quedó validada.
    """
    contenido = payload.contenido
    historia_id = contenido.get("historia_id")
    if not historia_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Falta 'historia_id'.")

    resultado = validar_historia(contenido)

    ultima_version = (
        db.query(func.max(Historia.version))
        .filter(Historia.historia_id == historia_id)
        .scalar()
    )
    nueva_version = (ultima_version or 0) + 1
    contenido["version"] = nueva_version

    historia = Historia(
        historia_id=historia_id,
        titulo=contenido.get("titulo", historia_id),
        version=nueva_version,
        contenido=contenido,
        validada=resultado.valida,
        errores_validacion=resultado.errores or None,
        publicada=False,
    )
    db.add(historia)
    db.commit()
    db.refresh(historia)
    return historia


@router.post(
    "/{historia_id}/publicar",
    response_model=HistoriaDetalle,
    dependencies=[Depends(requerir_admin)],
)
def publicar_historia(historia_id: str, db: Session = Depends(get_db)):
    """Publica la última versión validada de `historia_id`: a partir de
    ahora aparece en el selector del máster. Las versiones anteriores de la
    misma historia quedan despublicadas (solo la más reciente es visible),
    sin que eso afecte a las salas ya creadas con ellas."""
    historia = (
        db.query(Historia)
        .filter(Historia.historia_id == historia_id, Historia.validada.is_(True))
        .order_by(Historia.version.desc())
        .first()
    )
    if not historia:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No hay ninguna versión validada de esa historia."
        )

    db.query(Historia).filter(Historia.historia_id == historia_id).update({"publicada": False})
    historia.publicada = True
    db.commit()
    db.refresh(historia)
    return historia
