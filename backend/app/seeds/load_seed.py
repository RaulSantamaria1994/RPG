"""Carga las historias de ejemplo del directorio `seeds/` en la base de datos,
validándolas antes de insertarlas. Uso: python -m app.seeds.load_seed
"""

import json
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.engine.validator import validar_historia
from app.models.historia import Historia

SEEDS_DIR = Path(__file__).parent
HISTORIAS_SEED = ["cuervo_negro.json", "ala_norte.json", "frecuencia_negra.json"]


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
