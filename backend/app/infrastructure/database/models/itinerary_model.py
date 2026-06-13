import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, JSON, ForeignKey, func
from app.infrastructure.database.types import GUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ItineraryModel(Base):
    __tablename__ = "itineraries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True, index=True
    )

    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    total_estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)

    # Estructuras anidadas se guardan como JSON (highlights, days, practical_info, preferences)
    highlights: Mapped[list] = mapped_column(JSON, nullable=False)
    days: Mapped[list] = mapped_column(JSON, nullable=False)
    practical_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False)

    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
