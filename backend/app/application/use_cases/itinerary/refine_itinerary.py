from uuid import UUID

from app.domain.entities.itinerary import Itinerary
from app.domain.repositories.itinerary_repository import ItineraryRepository
from app.domain.services.llm_service import LLMService
from app.application.use_cases.itinerary.validate_itinerary import (
    ItineraryValidator,
    ItineraryValidationError,
)


class RefineItineraryUseCase:
    """
    Permite al usuario pedir cambios en lenguaje natural sobre un itinerario existente
    (ej: "quiero menos museos, más playa"). Punto 8 del enunciado: modificaciones.
    """

    MAX_RETRIES = 2

    def __init__(
        self,
        llm_service: LLMService,
        itinerary_repository: ItineraryRepository,
        validator: ItineraryValidator,
    ):
        self._llm = llm_service
        self._itineraries = itinerary_repository
        self._validator = validator

    async def execute(self, itinerary_id: UUID, instruction: str) -> Itinerary:
        itinerary = await self._itineraries.get_by_id(itinerary_id)
        if not itinerary:
            raise ValueError("Itinerario no encontrado.")

        last_error = None
        for _ in range(self.MAX_RETRIES + 1):
            refined = await self._llm.refine_itinerary(itinerary, instruction)
            try:
                self._validator.validate(refined, itinerary.preferences)
                refined.id = itinerary.id
                refined.user_id = itinerary.user_id
                return refined
            except ItineraryValidationError as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"No se pudo refinar el itinerario. Último error: {last_error}")
