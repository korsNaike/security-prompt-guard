"""remove text mood catalog

Revision ID: 20260509_0008
Revises: 20260509_0007
Create Date: 2026-05-09 00:08:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0008"
down_revision: str | None = "20260509_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE model_pricing SET is_active = false WHERE model_code = 'text_mood'")
    )
    op.execute(sa.text("UPDATE ml_models SET is_active = false WHERE model_code = 'text_mood'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE ml_models SET is_active = true WHERE model_code = 'text_mood'"))
    op.execute(
        sa.text("UPDATE model_pricing SET is_active = true WHERE model_code = 'text_mood'")
    )
