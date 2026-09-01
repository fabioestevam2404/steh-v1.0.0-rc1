"""Alpha 0.4 implementation layer."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_alpha_0_4"
down_revision: str | None = "0002_alpha_0_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("implementation", sa.JSON(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("tasks", "implementation")
