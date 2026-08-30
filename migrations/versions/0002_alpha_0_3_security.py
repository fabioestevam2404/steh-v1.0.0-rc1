"""Alpha 0.3 security domain."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_alpha_0_3"
down_revision: Union[str, None] = "0001_alpha_0_2_1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("security_review", sa.JSON(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("risk_level", sa.String(length=16), nullable=True),
    )
    op.create_index("ix_tasks_risk_level", "tasks", ["risk_level"])

    op.create_table(
        "security_findings",
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("affected_component", sa.String(length=255), nullable=False),
        sa.Column("threat", sa.String(length=100), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_security_findings_task_id", "security_findings", ["task_id"])
    op.create_index("ix_security_findings_trace_id", "security_findings", ["trace_id"])
    op.create_index("ix_security_findings_severity", "security_findings", ["severity"])
    op.create_index("ix_security_findings_category", "security_findings", ["category"])
    op.create_index("ix_security_findings_status", "security_findings", ["status"])


def downgrade() -> None:
    op.drop_table("security_findings")
    op.drop_index("ix_tasks_risk_level", table_name="tasks")
    op.drop_column("tasks", "risk_level")
    op.drop_column("tasks", "security_review")
