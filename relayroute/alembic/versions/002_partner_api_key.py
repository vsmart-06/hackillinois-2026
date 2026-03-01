"""Add partner API key column

Revision ID: 002_partner_api_key
Revises: 001_initial
Create Date: 2026-03-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_partner_api_key"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "partners",
        sa.Column("api_key", sa.String(length=255), nullable=False, server_default=sa.text("''")),
    )


def downgrade() -> None:
    op.drop_column("partners", "api_key")
