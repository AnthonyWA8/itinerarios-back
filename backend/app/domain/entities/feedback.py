from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Feedback:
    id: Optional[UUID]
    itinerary_id: UUID
    user_id: UUID
    rating: int  # 1-5
    liked_activity_titles: list[str]
    comment: Optional[str]
    created_at: Optional[datetime] = None
