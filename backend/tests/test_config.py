"""Normalización de DATABASE_URL: Railway, Render y la mayoría de
proveedores de Postgres gestionado inyectan la URL con el esquema genérico
("postgres://" o "postgresql://"), no el que necesita SQLAlchemy para
elegir el driver psycopg3 que trae este proyecto — sin esto, el backend
arranca contra esa URL tal cual y falla al intentar cargar psycopg2.
"""

from app.config import Settings


def test_normaliza_esquema_postgres_corto():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_normaliza_esquema_postgresql():
    s = Settings(database_url="postgresql://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_no_toca_una_url_ya_con_driver_explicito():
    s = Settings(database_url="postgresql+psycopg://u:p@host:5432/db")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"
