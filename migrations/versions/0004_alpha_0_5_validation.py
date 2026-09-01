"""Alpha 0.5 validation and rework."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_alpha_0_5"
down_revision: str | None = "0003_alpha_0_4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "validation",
            sa.JSON(),
            nullable=True,
        ),
    )

    op.add_column(
        "tasks",
        sa.Column(
            "rework_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "tasks",
        "rework_count",
    )

    op.drop_column(
        "tasks",
        "validation",
    )