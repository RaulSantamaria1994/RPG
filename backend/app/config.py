from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rpg:rpg@localhost:5432/rpg_dev"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    codigo_sala_longitud: int = 6
    sala_max_jugadores_duro: int = 6

    # Una sala sin ninguna actividad (ninguna petición REST ni mensaje WS que
    # toque `ultima_actividad_en`) durante este número de días se considera
    # abandonada y se borra, junto con su estado, personajes e inventario.
    sala_expiracion_dias: int = 30
    # Cada cuánto se ejecuta esa limpieza en segundo plano, en horas.
    limpieza_intervalo_horas: int = 24


@lru_cache
def get_settings() -> Settings:
    return Settings()
