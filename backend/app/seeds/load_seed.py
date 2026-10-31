"""Carga las historias de ejemplo del directorio `seeds/` en la base de datos,
validándolas antes de insertarlas. Uso: python -m app.seeds.load_seed

Las 4 historias originales (cuervo_negro, ala_norte, frecuencia_negra,
lo_que_duerme_en_la_orilla) usan el esquema viejo (dificultad/atributo) y
quedan retiradas con la reestructuración a PbtA: ya no pasan el validador
nuevo, así que se sacan de la lista de siembra para no romper el arranque
en cada despliegue. Sus archivos y las filas ya existentes en la base de
datos de producción no se tocan (ver docs/motor_pbta_plan.md, sección 8;
la retirada de las filas publicadas vive en la migración de Alembic
correspondiente). La lista queda vacía hasta que haya historias de ejemplo
en el esquema nuevo (Fase 5: rediseño del artefacto de creación de historias).
"""

import json
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.engine.validator import validar_historia
from app.models.historia import Historia

SEEDS_DIR = Path(__file__).parent
HISTORIAS_SEED: list[str] = []


def cargar_historia(db, nombre_archivo: str) -> Historia:
    contenido = json.loads((SEEDS_DIR / nombre_archivo).read_text(encoding="utf-8"))
    resultado = validar_historia(contenido)
    if not resultado.valida:
        raise ValueError(
            f"La historia '{nombre_archivo}' no es válida: {resultado.errores}"
        )

    historia_id = contenido["historia_id"]
    version = contenido.get("version", 1)

    existente = (
        db.query(Historia)
        .filter(Historia.historia_id == historia_id, Historia.version == version)
        .first()
    )
    if existente:
        return existente

    historia = Historia(
        historia_id=historia_id,
        titulo=contenido["titulo"],
        version=version,
        contenido=contenido,
        validada=True,
        errores_validacion=None,
        publicada=True,
    )
    db.add(historia)
    db.flush()
    return historia


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for nombre_archivo in HISTORIAS_SEED:
            historia = cargar_historia(db, nombre_archivo)
            print(f"OK: {historia.titulo} v{historia.version} ({historia.historia_id})")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
