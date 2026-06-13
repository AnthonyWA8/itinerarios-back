from app.domain.entities.itinerary import TravelPreferences, Itinerary
from app.application.use_cases.itinerary.generate_itinerary import GenerateItineraryUseCase


class RegenerateItineraryUseCase:
    """Misma lógica que generar, pero indicando al LLM que evite repetir la versión previa."""

    def __init__(self, generate_use_case: GenerateItineraryUseCase):
        self._generate = generate_use_case

    async def execute(self, preferences: TravelPreferences, user_id=None) -> Itinerary:
        return await self._generate.execute(preferences, user_id=user_id)
