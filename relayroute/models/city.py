from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from relayroute.models.base import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    epsilon_km: Mapped[float] = mapped_column(Float, nullable=False)
    min_restaurants_per_zone: Mapped[int] = mapped_column(Integer, nullable=False)
    dropoff_spacing_km: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
