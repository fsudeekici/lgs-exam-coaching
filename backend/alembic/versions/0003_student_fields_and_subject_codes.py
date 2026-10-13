"""student school and class, subject codes from the seed file

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old subject codes -> codes used in seed/lgs_topics_seed.json, so the seed
# updates the existing subjects instead of creating duplicates.
SUBJECT_CODES = {
    'turkish': 'turkce',
    'history': 'inkilap',
    'religion': 'din',
    'english': 'ingilizce',
    'math': 'matematik',
    'science': 'fen',
}


def rename_subject_codes(codes: dict[str, str]) -> None:
    subjects = sa.table('subjects', sa.column('code', sa.String))
    for old, new in codes.items():
        op.execute(subjects.update().where(subjects.c.code == old).values(code=new))


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('school', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('class_name', sa.String(length=50), nullable=True))
    rename_subject_codes(SUBJECT_CODES)


def downgrade() -> None:
    """Downgrade schema."""
    rename_subject_codes({new: old for old, new in SUBJECT_CODES.items()})
    op.drop_column('users', 'class_name')
    op.drop_column('users', 'school')
