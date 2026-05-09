"""add mvp compliance batch item costs

Revision ID: 20260509_0006
Revises: 20260509_0005
Create Date: 2026-05-09 00:06:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260509_0006"
down_revision: str | None = "20260509_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "classification_batch_items",
        sa.Column("estimated_cost", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "classification_batch_items",
        sa.Column("final_cost", sa.Integer(), nullable=True),
    )
    op.alter_column("classification_batch_items", "estimated_cost", server_default=None)


def downgrade() -> None:
    op.drop_column("classification_batch_items", "final_cost")
    op.drop_column("classification_batch_items", "estimated_cost")
