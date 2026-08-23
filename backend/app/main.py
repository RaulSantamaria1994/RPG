from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import historias, personajes, salas
from app.websockets.sala_ws import router as ws_router

app = FastAPI(title="RPG narrativo cooperativo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
