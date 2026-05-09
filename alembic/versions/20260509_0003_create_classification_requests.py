"""create classification requests

Revision ID: 20260509_0003
Revises: 20260509_0002
Create Date: 2026-05-09 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0003"
down_revision: str | None = "20260509_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "classification_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("model_code", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("estimated_cost", sa.Integer(), nullable=False),
        sa.Column("final_cost", sa.Integer(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classification_requests_input_hash"),
        "classification_requests",
        ["input_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classification_requests_model_code"),
        "classification_requests",
        ["model_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classification_requests_status"),
        "classification_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classification_requests_user_id"),
        "classification_requests",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "classification_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("recommended_action", sa.String(length=100), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("raw_scores", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("model_code", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["classification_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        op.f("ix_classification_results_request_id"),
        "classification_results",
        ["request_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_billing_transactions_classification_request_id",
        "billing_transactions",
        "classification_requests",
        ["classification_request_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_billing_transactions_classification_request_id",
        "billing_transactions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_classification_results_request_id"), table_name="classification_results")
    op.drop_table("classification_results")
    op.drop_index(op.f("ix_classification_requests_user_id"), table_name="classification_requests")
    op.drop_index(op.f("ix_classification_requests_status"), table_name="classification_requests")
    op.drop_index(
        op.f("ix_classification_requests_model_code"),
        table_name="classification_requests",
    )
    op.drop_index(
        op.f("ix_classification_requests_input_hash"),
        table_name="classification_requests",
    )
    op.drop_table("classification_requests")
