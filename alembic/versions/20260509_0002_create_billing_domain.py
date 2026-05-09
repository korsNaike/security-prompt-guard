from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0002"
down_revision: str | None = "20260509_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("loyalty_tiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("min_monthly_predictions", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.add_column("users", sa.Column("loyalty_tier_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_loyalty_tier_id_loyalty_tiers",
        "users",
        "loyalty_tiers",
        ["loyalty_tier_id"],
        ["id"],
    )

    op.create_table("billing_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("classification_request_id", sa.Uuid(), nullable=True),
        sa.Column("related_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["related_transaction_id"], ["billing_transactions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_billing_transactions_user_id"),
        "billing_transactions",
        ["user_id"],
        unique=False,
    )

    op.create_table("promo_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("credits_amount", sa.Integer(), nullable=False),
        sa.Column("max_activations", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table("promo_code_activations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("promo_code_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("credits_granted", sa.Integer(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["promo_code_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("promo_code_id", "user_id", name="uq_promo_code_activations_code_user"),
    )

    op.create_table("loyalty_tier_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("old_tier_id", sa.Uuid(), nullable=True),
        sa.Column("new_tier_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predictions_count", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["new_tier_id"], ["loyalty_tiers.id"]),
        sa.ForeignKeyConstraint(["old_tier_id"], ["loyalty_tiers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("loyalty_tier_history")
    op.drop_table("promo_code_activations")
    op.drop_table("promo_codes")
    op.drop_index(op.f("ix_billing_transactions_user_id"), table_name="billing_transactions")
    op.drop_table("billing_transactions")
    op.drop_constraint("fk_users_loyalty_tier_id_loyalty_tiers", "users", type_="foreignkey")
    op.drop_column("users", "loyalty_tier_id")
    op.drop_table("loyalty_tiers")
