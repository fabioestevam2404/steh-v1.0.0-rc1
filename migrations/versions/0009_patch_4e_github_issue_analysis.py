"""Add GitHub issue snapshot and analysis artifacts to tasks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_patch_4e_issue_analysis"
down_revision: str | None = "0008_patch_4d_context_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("source_issue", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("issue_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "issue_analysis")
    op.drop_column("tasks", "source_issue")
