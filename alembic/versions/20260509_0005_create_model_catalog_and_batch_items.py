"""create model catalog and batch items

Revision ID: 20260509_0005
Revises: 20260509_0004
Create Date: 2026-05-09 00:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0005"
down_revision: str | None = "20260509_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_code", sa.String(length=100), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_code"),
    )
    op.create_index(op.f("ix_ml_models_model_code"), "ml_models", ["model_code"], unique=False)

    op.create_table(
        "model_pricing",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_code", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["model_code"], ["ml_models.model_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_code", "mode", name="uq_model_pricing_model_mode"),
    )
    op.create_index(
        op.f("ix_model_pricing_model_code"),
        "model_pricing",
        ["model_code"],
        unique=False,
    )

    op.create_table(
        "classification_batch_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("classification_request_id", sa.Uuid(), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["classification_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["classification_request_id"],
            ["classification_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "item_index", name="uq_classification_batch_items_index"),
        sa.UniqueConstraint(
            "classification_request_id",
            name="uq_classification_batch_items_request",
        ),
    )
    op.create_index(
        op.f("ix_classification_batch_items_batch_id"),
        "classification_batch_items",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classification_batch_items_classification_request_id"),
        "classification_batch_items",
        ["classification_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classification_batch_items_status"),
        "classification_batch_items",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_classification_batch_items_status"),
        table_name="classification_batch_items",
    )
    op.drop_index(
        op.f("ix_classification_batch_items_classification_request_id"),
        table_name="classification_batch_items",
    )
    op.drop_index(
        op.f("ix_classification_batch_items_batch_id"),
        table_name="classification_batch_items",
    )
    op.drop_table("classification_batch_items")
    op.drop_index(op.f("ix_model_pricing_model_code"), table_name="model_pricing")
    op.drop_table("model_pricing")
    op.drop_index(op.f("ix_ml_models_model_code"), table_name="ml_models")
    op.drop_table("ml_models")
