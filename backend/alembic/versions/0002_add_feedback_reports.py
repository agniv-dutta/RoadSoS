"""add feedback reports table

Revision ID: 0002_add_feedback_reports
Revises: 0001_initial_schema
Create Date: 2026-05-31 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_feedback_reports'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, 'feedback_reports'):
        op.create_table(
            'feedback_reports',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column('place_id', sa.Integer(), nullable=True),
            sa.Column('issue', sa.String(length=512), nullable=False),
            sa.Column('correct_value', sa.String(length=512), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['place_id'], ['places.id']),
        )

    for index_name, columns in (
        ('ix_feedback_reports_place_id', ['place_id']),
        ('ix_feedback_reports_created_at', ['created_at']),
    ):
        if not _index_exists(bind, 'feedback_reports', index_name):
            op.create_index(index_name, 'feedback_reports', columns)


def downgrade() -> None:
    op.drop_index('ix_feedback_reports_created_at', table_name='feedback_reports')
    op.drop_index('ix_feedback_reports_place_id', table_name='feedback_reports')
    op.drop_table('feedback_reports')
