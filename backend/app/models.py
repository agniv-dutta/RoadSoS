from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


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
