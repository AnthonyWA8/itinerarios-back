from uuid import UUID

from app.domain.entities.itinerary import Itinerary
from app.domain.repositories.itinerary_repository import ItineraryRepository


class GetUserItinerariesUseCase:
    def __init__(self, itinerary_repository: ItineraryRepository):
        self._itineraries = itinerary_repository

    async def execute(self, user_id: UUID) -> list[Itinerary]:
        return await self._itineraries.get_by_user(user_id)


class DeleteItineraryUseCase:
    def __init__(self, itinerary_repository: ItineraryRepository):
        self._itineraries = itinerary_repository

    async def execute(self, itinerary_id: UUID, user_id: UUID) -> None:
        await self._itineraries.delete(itinerary_id, user_id)
