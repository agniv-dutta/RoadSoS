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


def upgrade() -> None:
    op.create_table(
        'feedback_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('place_id', sa.Integer(), nullable=True),
        sa.Column('issue', sa.String(length=512), nullable=False),
        sa.Column('correct_value', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['place_id'], ['places.id']),
    )
    op.create_index('ix_feedback_reports_place_id', 'feedback_reports', ['place_id'])
    op.create_index('ix_feedback_reports_created_at', 'feedback_reports', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_feedback_reports_created_at', table_name='feedback_reports')
    op.drop_index('ix_feedback_reports_place_id', table_name='feedback_reports')
    op.drop_table('feedback_reports')
