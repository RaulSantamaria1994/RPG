"""elimina tablas en desuso

Revision ID: bdc8fc5b6263
Revises: 4ed128edb681
Create Date: 2026-10-13 00:00:00.000000

`historial_decisiones` y `objetos` se crearon en el esquema inicial pero
nunca llegaron a usarse: el log de partida vive solo en memoria del cliente
(reconstruido a partir de los mensajes del WebSocket) y el inventario usa
listas JSON en `estado_sala`/`personajes`, no esta tabla.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.models.types


# revision identifiers, used by Alembic.
revision: str = 'bdc8fc5b6263'
down_revision: Union[str, None] = '4ed128edb681'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('objetos')
    op.drop_table('historial_decisiones')


def downgrade() -> None:
    op.create_table('historial_decisiones',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('sala_id', sa.Uuid(), nullable=False),
    sa.Column('personaje_id', sa.Uuid(), nullable=True),
    sa.Column('nodo_id', sa.String(length=60), nullable=False),
    sa.Column('palabra_clave_texto', sa.String(length=200), nullable=True),
    sa.Column('tipo_interaccion', sa.String(length=40), nullable=True),
    sa.Column('resultado', sa.String(length=20), nullable=True),
    sa.Column('tirada', app.models.types.JSONVariant(), nullable=True),
    sa.Column('nodo_destino_id', sa.String(length=60), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['personaje_id'], ['personajes.id'], ),
    sa.ForeignKeyConstraint(['sala_id'], ['salas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('objetos',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('sala_id', sa.Uuid(), nullable=False),
    sa.Column('objeto_id', sa.String(length=60), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('descripcion', sa.String(length=500), nullable=True),
    sa.Column('consumible', sa.Boolean(), nullable=False),
    sa.Column('efecto', app.models.types.JSONVariant(), nullable=True),
    sa.Column('ubicacion', sa.String(length=20), nullable=False),
    sa.Column('personaje_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['personaje_id'], ['personajes.id'], ),
    sa.ForeignKeyConstraint(['sala_id'], ['salas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
