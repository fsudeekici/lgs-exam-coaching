"""subject short name and session

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# code -> (short_name, session), same values as seed/lgs_topics_seed.json.
# Existing rows need them before the columns can become NOT NULL.
SUBJECTS = {
    'turkce': ('Türkçe', 'sozel'),
    'inkilap': ('İnkılap', 'sozel'),
    'din': ('Din', 'sozel'),
    'ingilizce': ('İngilizce', 'sozel'),
    'matematik': ('Mat', 'sayisal'),
    'fen': ('Fen', 'sayisal'),
}


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('subjects', sa.Column('short_name', sa.String(length=32), nullable=True))
    op.add_column('subjects', sa.Column('session', sa.String(length=16), nullable=True))

    subjects = sa.table(
        'subjects',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('short_name', sa.String),
        sa.column('session', sa.String),
    )
    for code, (short_name, session) in SUBJECTS.items():
        op.execute(subjects.update().where(subjects.c.code == code).values(short_name=short_name, session=session))
    # Any subject outside the LGS six: fall back so the migration cannot fail; the seed sets real values.
    op.execute(
        subjects.update()
        .where(subjects.c.short_name.is_(None))
        .values(short_name=sa.func.left(subjects.c.name, 32), session='sozel')
    )

    op.alter_column('subjects', 'short_name', nullable=False)
    op.alter_column('subjects', 'session', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('subjects', 'session')
    op.drop_column('subjects', 'short_name')
