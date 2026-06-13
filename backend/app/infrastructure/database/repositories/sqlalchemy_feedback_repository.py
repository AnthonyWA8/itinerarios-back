from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.feedback import Feedback
from app.domain.repositories.feedback_repository import FeedbackRepository
from app.infrastructure.database.models.feedback_model import FeedbackModel
from app.infrastructure.database.models.itinerary_model import ItineraryModel


class SQLAlchemyFeedbackRepository(FeedbackRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, feedback: Feedback) -> Feedback:
        model = FeedbackModel(
            id=feedback.id,
            itinerary_id=feedback.itinerary_id,
            user_id=feedback.user_id,
            rating=feedback.rating,
            liked_activity_titles=feedback.liked_activity_titles,
            comment=feedback.comment,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_itinerary(self, itinerary_id: UUID) -> list[Feedback]:
        result = await self._session.execute(
            select(FeedbackModel).where(FeedbackModel.itinerary_id == itinerary_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_all_for_training(self) -> list[Feedback]:
        result = await self._session.execute(select(FeedbackModel))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_average_rating_for_destination(self, destination: str) -> float | None:
        destination_key = destination.split(",")[0].strip()
        stmt = (
            select(func.avg(FeedbackModel.rating))
            .join(ItineraryModel, ItineraryModel.id == FeedbackModel.itinerary_id)
            .where(ItineraryModel.destination.ilike(f"%{destination_key}%"))
        )
        result = await self._session.execute(stmt)
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else None

    @staticmethod
    def _to_entity(model: FeedbackModel) -> Feedback:
        return Feedback(
            id=model.id,
            itinerary_id=model.itinerary_id,
            user_id=model.user_id,
            rating=model.rating,
            liked_activity_titles=model.liked_activity_titles,
            comment=model.comment,
            created_at=model.created_at,
        )
