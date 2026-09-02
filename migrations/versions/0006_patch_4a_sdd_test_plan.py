"""Add specification and test plan artifacts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_patch_4a_sdd_test_plan"
down_revision: str | None = "0005_alpha_0_5_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("specification", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("test_plan", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "test_plan")
    op.drop_column("tasks", "specification")
