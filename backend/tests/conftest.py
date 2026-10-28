import json
import os
import socket
import threading
import time
from pathlib import Path

# El DATABASE_URL debe fijarse antes de que se importe app.database, que crea
# el engine a nivel de módulo.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://rpg:rpg@localhost:5432/rpg_test"
)
os.environ.setdefault("ADMIN_TOKEN", "token-admin-de-pruebas")

import pytest  # noqa: E402
import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.engine.validator import validar_historia  # noqa: E402
from app.main import app  # noqa: E402
from app.models.historia import Historia  # noqa: E402

SEED_PATH = Path(__file__).resolve().parents[1] / "app" / "seeds" / "cuervo_negro.json"
SEED_PATH_ALA_NORTE = Path(__file__).resolve().parents[1] / "app" / "seeds" / "ala_norte.json"


@pytest.fixture(scope="session", autouse=True)
def _preparar_esquema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _limpiar_tablas():
    yield
    with engine.begin() as conn:
        for tabla in reversed(Base.metadata.sorted_tables):
            conn.execute(tabla.delete())


@pytest.fixture()
def db():
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def admin_headers() -> dict:
    return {"X-Admin-Token": os.environ["ADMIN_TOKEN"]}


@pytest.fixture()
def contenido_cuervo_negro() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def historia_cuervo_negro(db, contenido_cuervo_negro):
    resultado = validar_historia(contenido_cuervo_negro)
    assert resultado.valida, resultado.errores

    historia = Historia(
        historia_id=contenido_cuervo_negro["historia_id"],
        titulo=contenido_cuervo_negro["titulo"],
        version=1,
        contenido=contenido_cuervo_negro,
        validada=True,
        publicada=True,
    )
    db.add(historia)
    db.commit()
    db.refresh(historia)
    return historia


@pytest.fixture()
def contenido_ala_norte() -> dict:
    return json.loads(SEED_PATH_ALA_NORTE.read_text(encoding="utf-8"))


@pytest.fixture()
def historia_ala_norte(db, contenido_ala_norte):
    resultado = validar_historia(contenido_ala_norte)
    assert resultado.valida, resultado.errores

    historia = Historia(
        historia_id=contenido_ala_norte["historia_id"],
        titulo=contenido_ala_norte["titulo"],
        version=1,
        contenido=contenido_ala_norte,
        validada=True,
        publicada=True,
    )
    db.add(historia)
    db.commit()
    db.refresh(historia)
    return historia


@pytest.fixture()
def d20_siempre_veinte(monkeypatch):
    """Fuerza todas las tiradas (incluida iniciativa) a sacar 20, para probar
    caminos deterministas. Se parchea `secrets.randbelow` en vez de
    `tirar_d20` porque `combate.py` importa la función por nombre y un
    monkeypatch sobre `app.engine.dice.tirar_d20` no le llegaría.
    """
    monkeypatch.setattr("secrets.randbelow", lambda n: 19)


@pytest.fixture()
def d20_siempre_uno(monkeypatch):
    monkeypatch.setattr("secrets.randbelow", lambda n: 0)


@pytest.fixture()
def servidor_en_vivo(_preparar_esquema):
    """Servidor uvicorn real en un hilo aparte. Necesario para probar dos
    WebSockets concurrentes de verdad: TestClient abre cada websocket_connect
    en su propio hilo/portal anyio aislado, así que un broadcast desde una
    conexión hacia otra puede colgarse (visto al depurar el picker de nodos).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]

    config = uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning")
    server = uvicorn.Server(config)
    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()

    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("El servidor de pruebas no arrancó a tiempo.")

    yield f"http://127.0.0.1:{puerto}", f"ws://127.0.0.1:{puerto}"

    server.should_exit = True
    hilo.join(timeout=5)
