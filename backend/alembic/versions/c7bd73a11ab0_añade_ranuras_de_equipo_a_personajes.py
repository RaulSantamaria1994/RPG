"""añade ranuras de equipo a personajes

Revision ID: c7bd73a11ab0
Revises: bdc8fc5b6263
Create Date: 2026-10-14 09:09:40.621457

Cada personaje puede llevar equipada un arma (bono de daño en el ataque
normal) y un hechizo (un grimorio del inventario común que permite
lanzarlo aunque no esté en `hechizos_conocidos`). Ninguno de los dos es
obligatorio, de ahí que ambas columnas sean nullable sin default: un
personaje recién creado no lleva nada equipado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.models.types


# revision identifiers, used by Alembic.
revision: str = 'c7bd73a11ab0'
down_revision: Union[str, None] = 'bdc8fc5b6263'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('personajes', sa.Column('arma_equipada', app.models.types.JSONVariant(), nullable=True))
    op.add_column('personajes', sa.Column('hechizo_equipado', app.models.types.JSONVariant(), nullable=True))


def downgrade() -> None:
    op.drop_column('personajes', 'hechizo_equipado')
    op.drop_column('personajes', 'arma_equipada')
