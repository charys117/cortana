"""add channels.position for Discord sidebar ordering

Revision ID: 002
Revises: 001
Create Date: 2026-08-28

"""

import sqlalchemy as sa

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # nullable: threads have no position, and existing rows are backfilled
    # by the next /sync
    op.add_column("channels", sa.Column("position", sa.Integer()))


def downgrade() -> None:
    op.drop_column("channels", "position")
