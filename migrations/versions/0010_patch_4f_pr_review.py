"""Add GitHub pull request snapshot and review artifacts to tasks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_patch_4f_pr_review"
down_revision: str | None = "0009_patch_4e_issue_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("source_pull_request", sa.JSON(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("pull_request_review", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "pull_request_review")
    op.drop_column("tasks", "source_pull_request")
