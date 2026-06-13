from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.itinerary import Itinerary


class ItineraryRepository(ABC):
    @abstractmethod
    async def save(self, itinerary: Itinerary) -> Itinerary:
        ...

    @abstractmethod
    async def get_by_id(self, itinerary_id: UUID) -> Optional[Itinerary]:
        ...

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> list[Itinerary]:
        ...

    @abstractmethod
    async def delete(self, itinerary_id: UUID, user_id: UUID) -> None:
        ...
