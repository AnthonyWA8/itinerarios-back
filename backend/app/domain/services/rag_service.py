from abc import ABC, abstractmethod

from app.domain.entities.itinerary import TravelPreferences


class RAGService(ABC):
    @abstractmethod
    async def retrieve_context(
        self,
        preferences: TravelPreferences,
        top_k: int = 5,
    ) -> list[str]:
        """Recupera fragmentos relevantes (guías, reseñas) para el destino/intereses."""
        ...
