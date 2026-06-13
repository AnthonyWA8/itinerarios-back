import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, JSON, ForeignKey, func
from app.infrastructure.database.types import GUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class FeedbackModel(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("itineraries.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    liked_activity_titles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
