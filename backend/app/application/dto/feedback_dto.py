from typing import Optional

from pydantic import BaseModel, Field


class SubmitFeedbackRequest(BaseModel):
    itinerary_id: str
    rating: int = Field(ge=1, le=5)
    liked_activity_titles: list[str] = []
    comment: Optional[str] = None
