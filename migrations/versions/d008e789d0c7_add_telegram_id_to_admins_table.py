"""add telegram_id to admins table

Revision ID: d008e789d0c7
Revises: df60cb254816
Create Date: 2025-11-16 23:17:21.992113

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d008e789d0c7"
down_revision: Union[str, None] = "df60cb254816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add telegram_id column to admins table
    op.add_column(
        "admins", sa.Column("telegram_id", sa.String(50), unique=True, nullable=True)
    )


def downgrade() -> None:
    # Remove telegram_id column from admins table
    op.drop_column("admins", "telegram_id")
