from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rpg:rpg@localhost:5432/rpg_dev"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # Token fijo (no JWT) para los endpoints de administración de contenido
    # (subir/publicar historias). Vacío por defecto: con él vacío, esos
    # endpoints rechazan cualquier petición — hay que fijarlo explícitamente
    # por variable de entorno antes de poder usarlos en ningún entorno.
    admin_token: str = ""

    codigo_sala_longitud: int = 6
    sala_max_jugadores_duro: int = 6

    # Una sala sin ninguna actividad (ninguna petición REST ni mensaje WS que
    # toque `ultima_actividad_en`) durante este número de días se considera
    # abandonada y se borra, junto con su estado, personajes e inventario.
    sala_expiracion_dias: int = 30
    # Cada cuánto se ejecuta esa limpieza en segundo plano, en horas.
    limpieza_intervalo_horas: int = 24

    @field_validator("database_url")
    @classmethod
    def _usar_driver_psycopg(cls, v: str) -> str:
        # Railway, Render y la mayoría de proveedores inyectan la URL de
        # Postgres con el esquema genérico "postgres://"/"postgresql://" (el
        # que entiende libpq), no el que espera SQLAlchemy para elegir el
        # driver psycopg3 que trae este proyecto. Sin esto, arrancar contra
        # esa URL tal cual falla porque SQLAlchemy intenta cargar psycopg2.
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
