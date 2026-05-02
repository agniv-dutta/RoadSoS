"""initial schema for RoadSoS

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial RoadSoS tables."""

    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("place_type", sa.String(length=50), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("address", sa.String(length=512), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("geohash5", sa.String(length=5), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_places_lat_lng", "places", ["latitude", "longitude"])
    op.create_index("ix_places_type_geohash", "places", ["place_type", "geohash5"])
    op.create_index("ix_places_name", "places", ["name"])
    op.create_index("ix_places_place_type", "places", ["place_type"])
    op.create_index("ix_places_geohash5", "places", ["geohash5"])
    op.create_index("ix_places_source", "places", ["source"])

    op.create_table(
        "sos_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("sms_sent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("whatsapp_sent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("nearest_hospital_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["nearest_hospital_id"], ["places.id"]),
    )
    op.create_index("ix_sos_logs_latitude", "sos_logs", ["latitude"])
    op.create_index("ix_sos_logs_longitude", "sos_logs", ["longitude"])
    op.create_index("ix_sos_logs_nearest_hospital_id", "sos_logs", ["nearest_hospital_id"])


def downgrade() -> None:
    """Drop the initial RoadSoS tables."""

    op.drop_index("ix_sos_logs_nearest_hospital_id", table_name="sos_logs")
    op.drop_index("ix_sos_logs_longitude", table_name="sos_logs")
    op.drop_index("ix_sos_logs_latitude", table_name="sos_logs")
    op.drop_table("sos_logs")

    op.drop_index("ix_places_source", table_name="places")
    op.drop_index("ix_places_geohash5", table_name="places")
    op.drop_index("ix_places_place_type", table_name="places")
    op.drop_index("ix_places_name", table_name="places")
    op.drop_index("ix_places_type_geohash", table_name="places")
    op.drop_index("ix_places_lat_lng", table_name="places")
    op.drop_table("places")
