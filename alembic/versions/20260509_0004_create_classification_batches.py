"""create classification batches

Revision ID: 20260509_0004
Revises: 20260509_0003
Create Date: 2026-05-09 00:04:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0004"
down_revision: str | None = "20260509_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "classification_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("completed_requests", sa.Integer(), nullable=False),
        sa.Column("failed_requests", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Integer(), nullable=False),
        sa.Column("final_cost", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classification_batches_status"),
        "classification_batches",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classification_batches_user_id"),
        "classification_batches",
        ["user_id"],
        unique=False,
    )
    op.add_column("classification_requests", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_classification_requests_batch_id"),
        "classification_requests",
        ["batch_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_classification_requests_batch_id",
        "classification_requests",
        "classification_batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_classification_requests_batch_id",
        "classification_requests",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_classification_requests_batch_id"), table_name="classification_requests")
    op.drop_column("classification_requests", "batch_id")
    op.drop_index(op.f("ix_classification_batches_user_id"), table_name="classification_batches")
    op.drop_index(op.f("ix_classification_batches_status"), table_name="classification_batches")
    op.drop_table("classification_batches")
