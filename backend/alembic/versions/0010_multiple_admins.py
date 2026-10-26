"""multiple admins: main admin flag and each student's coach

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('coach_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_coach_id'), 'users', ['coach_id'], unique=False)
    op.create_foreign_key('users_coach_id_fkey', 'users', 'users', ['coach_id'], ['id'], ondelete='SET NULL')

    # Until now there was a single admin: it becomes the main admin and keeps every student and parent.
    op.execute(
        "UPDATE users SET is_superadmin = true "
        "WHERE id = (SELECT min(id) FROM users WHERE role = 'admin')"
    )
    op.execute(
        "UPDATE users SET coach_id = (SELECT min(id) FROM users WHERE role = 'admin') "
        "WHERE role IN ('student', 'parent')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('users_coach_id_fkey', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_coach_id'), table_name='users')
    op.drop_column('users', 'coach_id')
    op.drop_column('users', 'is_superadmin')
