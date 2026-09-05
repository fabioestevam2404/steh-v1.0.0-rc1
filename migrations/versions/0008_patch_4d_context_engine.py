"""Add immutable context bundle snapshots to tasks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_patch_4d_context_engine"
down_revision: str | None = "0007_patch_4c_human_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("context_bundle", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "context_bundle")
