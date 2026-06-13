from datetime import datetime, timezone
from uuid import uuid4, UUID

from app.domain.entities.feedback import Feedback
from app.domain.repositories.feedback_repository import FeedbackRepository


class SubmitFeedbackUseCase:
    def __init__(self, feedback_repository: FeedbackRepository):
        self._feedback = feedback_repository

    async def execute(
        self,
        itinerary_id: UUID,
        user_id: UUID,
        rating: int,
        liked_activity_titles: list[str],
        comment: str | None,
    ) -> Feedback:
        feedback = Feedback(
            id=uuid4(),
            itinerary_id=itinerary_id,
            user_id=user_id,
            rating=rating,
            liked_activity_titles=liked_activity_titles,
            comment=comment,
            created_at=datetime.now(timezone.utc),
        )
        return await self._feedback.save(feedback)
