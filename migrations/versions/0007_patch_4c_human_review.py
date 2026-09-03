"""Add persisted human-review state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_patch_4c_human_review"
down_revision: str | None = "0006_patch_4a_sdd_test_plan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("human_review", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "human_review")
