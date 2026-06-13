from uuid import UUID

from app.domain.entities.itinerary import Itinerary
from app.domain.repositories.itinerary_repository import ItineraryRepository


class SaveItineraryUseCase:
    def __init__(self, itinerary_repository: ItineraryRepository):
        self._itineraries = itinerary_repository

    async def execute(self, itinerary: Itinerary, user_id: UUID, note: str | None = None) -> Itinerary:
        itinerary.user_id = user_id
        itinerary.note = note
        return await self._itineraries.save(itinerary)
