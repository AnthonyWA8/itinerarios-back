from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.feedback import Feedback


class FeedbackRepository(ABC):
    @abstractmethod
    async def save(self, feedback: Feedback) -> Feedback:
        ...

    @abstractmethod
    async def get_by_itinerary(self, itinerary_id: UUID) -> list[Feedback]:
        ...

    @abstractmethod
    async def get_all_for_training(self) -> list[Feedback]:
        """Usado en fases posteriores para construir el dataset de RLHF."""
        ...

    @abstractmethod
    async def get_average_rating_for_destination(self, destination: str) -> float | None:
        """Promedio de ratings de itinerarios pasados para un destino similar (RLHF-lite)."""
        ...
