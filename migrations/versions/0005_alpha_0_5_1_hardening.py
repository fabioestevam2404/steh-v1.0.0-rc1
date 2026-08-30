"""Alpha 0.5.1 scanner and rework evidence."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_alpha_0_5_1"
down_revision: Union[str, None] = "0004_alpha_0_5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("tasks", sa.Column("external_scan", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("rework_decision", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("tasks", "rework_decision")
    op.drop_column("tasks", "external_scan")
