from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from relayroute.models.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    city_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    restaurant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    delivery_address: Mapped[str] = mapped_column(String(512), nullable=False)
    delivery_lat: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_lng: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    relay_chain: Mapped[list] = mapped_column(JSONB, nullable=False)
    current_dropoff_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_handoffs: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_handoffs: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
