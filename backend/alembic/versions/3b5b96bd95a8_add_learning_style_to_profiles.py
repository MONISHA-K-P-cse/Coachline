"""Add learning_style to profiles

Revision ID: 3b5b96bd95a8
Revises: b656fb611a90
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b5b96bd95a8'
down_revision: Union[str, None] = 'b656fb611a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column('learning_style', sa.String(), nullable=False, server_default='reading_writing'),
    )
    op.alter_column('profiles', 'learning_style', server_default=None)


def downgrade() -> None:
    op.drop_column('profiles', 'learning_style')
