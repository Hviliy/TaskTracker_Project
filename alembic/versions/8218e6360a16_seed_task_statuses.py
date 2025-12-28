"""seed task statuses

Revision ID: 8218e6360a16
Revises: bcd515cb3827
Create Date: 2025-12-29 02:51:58.208277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8218e6360a16'
down_revision: Union[str, Sequence[str], None] = 'bcd515cb3827'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    task_statuses = sa.table(
        "task_statuses",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_terminal", sa.Boolean)
    )

    op.bulk_insert(
        task_statuses,
        [
            {"code": "new", "name": "Новая", "sort_order": 10, "is_terminal": False},
            {"code": "in_progress", "name": "В работе", "sort_order": 20, "is_terminal": False},
            {"code": "review", "name": "На проверке", "sort_order": 30, "is_terminal": False},
            {"code": "done", "name": "Сделано", "sort_order": 40, "is_terminal": True},
        ],
    )

def downgrade() -> None:
    op.execute("DELETE FROM task_statuses WHERE code IN ('new','in_progress','review','done')")