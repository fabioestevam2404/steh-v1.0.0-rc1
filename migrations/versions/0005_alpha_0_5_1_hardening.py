"""Alpha 0.5.1 scanner and rework evidence."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_alpha_0_5_1"
down_revision: str | None = "0004_alpha_0_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("tasks", sa.Column("external_scan", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("rework_decision", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("tasks", "rework_decision")
    op.drop_column("tasks", "external_scan")
