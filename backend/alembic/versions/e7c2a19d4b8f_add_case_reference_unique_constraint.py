"""add case_reference unique constraint

Revision ID: e7c2a19d4b8f
Revises: 3d3cf359c2a1
Create Date: 2026-08-27 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7c2a19d4b8f"
down_revision: Union[str, Sequence[str], None] = "3d3cf359c2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add unique constraint to incidents.case_reference."""
    op.create_unique_constraint(
        op.f("uq_incidents_case_reference"),
        "incidents",
        ["case_reference"],
    )


def downgrade() -> None:
    """Downgrade schema: drop unique constraint from incidents.case_reference."""
    op.drop_constraint(
        op.f("uq_incidents_case_reference"),
        "incidents",
        type_="unique",
    )
