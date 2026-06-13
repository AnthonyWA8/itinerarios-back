from abc import ABC, abstractmethod

from app.domain.entities.itinerary import Itinerary, TravelPreferences


class LLMService(ABC):
    @abstractmethod
    async def generate_itinerary(
        self,
        preferences: TravelPreferences,
        context_chunks: list[str],
        avoid_previous: bool = False,
    ) -> Itinerary:
        """Genera un itinerario usando el LLM, opcionalmente con contexto RAG."""
        ...

    @abstractmethod
    async def refine_itinerary(
        self,
        itinerary: Itinerary,
        instruction: str,
    ) -> Itinerary:
        """Modifica un itinerario existente según instrucción del usuario."""
        ...
