from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def compute_data_confidence(*, is_verified: bool, source: str, last_synced: datetime | None) -> float:
    """Compute trust score for a place record based on source and freshness."""

    if is_verified:
        return 1.0

    source_key = (source or "").strip().lower()
    if source_key in {"google_places", "google"}:
        if last_synced is None:
            return 0.4
        synced_age = datetime.now(timezone.utc) - last_synced
        return 0.85 if synced_age.total_seconds() <= 7 * 24 * 3600 else 0.6
    if source_key in {"osm", "openstreetmap"}:
        return 0.6
    return 0.4


class Place(Base):
    """Cached roadside assistance place record."""

    __tablename__ = "places"
    __table_args__ = (
        Index("ix_places_type_geohash", "place_type", "geohash5"),
        Index("ix_places_lat_lng", "latitude", "longitude"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    place_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    geohash5: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    last_synced: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SOSLog(Base):
    """Log entry for an emergency SOS request."""

    __tablename__ = "sos_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nearest_hospital_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class FeedbackReport(Base):
    """Operator and citizen feedback on place data quality."""

    __tablename__ = "feedback_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    issue: Mapped[str] = mapped_column(String(512), nullable=False)
    correct_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
