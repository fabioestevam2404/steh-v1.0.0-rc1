"""Alpha 0.4 implementation layer."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_alpha_0_4"
down_revision: Union[str, None] = "0002_alpha_0_3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("implementation", sa.JSON(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("tasks", "implementation")
