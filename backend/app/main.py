import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.mantenimiento import limpiar_salas_expiradas
from app.routers import historias, personajes, salas
from app.websockets.router import router as ws_router

settings = get_settings()
logger = logging.getLogger("app.mantenimiento")


async def _tarea_limpieza_periodica() -> None:
    """Purga salas abandonadas cada `limpieza_intervalo_horas`, mientras dure
    el proceso. Corre una pasada nada más arrancar (para no esperar un ciclo
    entero tras cada despliegue) y luego se repite indefinidamente; un fallo
    en una pasada se registra y no debe impedir la siguiente.
    """
    intervalo_segundos = settings.limpieza_intervalo_horas * 3600
    while True:
        db = SessionLocal()
        try:
            borradas = limpiar_salas_expiradas(db)
            if borradas:
                logger.info("Limpieza de salas: %d sala(s) expirada(s) borradas.", borradas)
        except Exception:
            logger.exception("Fallo al limpiar salas expiradas.")
        finally:
            db.close()
        await asyncio.sleep(intervalo_segundos)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarea = asyncio.create_task(_tarea_limpieza_periodica())
    yield
    tarea.cancel()


app = FastAPI(title="RPG narrativo cooperativo", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # "*" junto con allow_credentials=True es una combinación inválida según
    # el spec de CORS: el navegador se niega a adjuntar la cabecera
    # Access-Control-Allow-Origin y las peticiones fallan con un error de
    # CORS que no tiene nada que ver con el problema real. La app no usa
    # cookies (la autenticación va siempre por cabecera Authorization), así
    # que no hace falta allow_credentials.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(salas.router)
app.include_router(personajes.router)
app.include_router(historias.router)
app.include_router(ws_router)


@app.get("/salud")
def salud():
    return {"estado": "ok"}
