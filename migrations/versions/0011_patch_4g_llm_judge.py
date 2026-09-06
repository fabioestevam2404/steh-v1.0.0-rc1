"""Add the non-authoritative judge evaluation artifact to tasks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_patch_4g_llm_judge"
down_revision: str | None = "0010_patch_4f_pr_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("judge_evaluation", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "judge_evaluation")
