"""retira las 4 historias del esquema viejo

Revision ID: 5577f3b5cd8b
Revises: 66d3e8981246
Create Date: 2026-10-31 08:18:55.357261

Migración de datos (sin cambio de esquema): despublica las 4 historias que
usan el esquema viejo (dificultad/atributo/modo_interaccion), incompatible
con el validador PbtA nuevo (ver docs/motor_pbta_plan.md, sección 8). No se
borran ni los archivos del repo ni las filas de la base de datos — solo
dejan de aparecer en el selector del máster (`publicada=false`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5577f3b5cd8b'
down_revision: Union[str, None] = '66d3e8981246'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HISTORIAS_RETIRADAS = (
    "cuervo_negro",
    "ala_norte",
    "frecuencia_negra",
    "lo_que_duerme_en_la_orilla",
)


def upgrade() -> None:
    conn = op.get_bind()
    for historia_id in HISTORIAS_RETIRADAS:
        conn.execute(
            sa.text("UPDATE historias SET publicada = false WHERE historia_id = :h"),
            {"h": historia_id},
        )


def downgrade() -> None:
    # Vuelve a publicar solo la versión más reciente de cada una (mismo
    # criterio que el endpoint normal de publicación: nunca más de una
    # versión publicada a la vez de la misma historia).
    conn = op.get_bind()
    for historia_id in HISTORIAS_RETIRADAS:
        conn.execute(
            sa.text(
                "UPDATE historias SET publicada = true WHERE historia_id = :h "
                "AND version = (SELECT MAX(version) FROM historias WHERE historia_id = :h)"
            ),
            {"h": historia_id},
        )
