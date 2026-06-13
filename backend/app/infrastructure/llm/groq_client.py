import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.domain.entities.itinerary import (
    Activity,
    ActivityType,
    BudgetType,
    DayPlan,
    Itinerary,
    PracticalInfo,
    TravelPreferences,
)
from app.domain.services.llm_service import LLMService
from app.infrastructure.llm.prompt_templates import (
    SYSTEM_PROMPT,
    build_user_prompt,
    build_refine_prompt,
)

# Mapeo de tipos no estándar que el LLM podría inventar -> tipos válidos del enum.
# Actúa como red de seguridad ante alucinaciones de categorías.
ACTIVITY_TYPE_FALLBACKS: dict[str, ActivityType] = {
    "beach": ActivityType.OUTDOOR,
    "nature": ActivityType.OUTDOOR,
    "adventure": ActivityType.OUTDOOR,
    "hiking": ActivityType.OUTDOOR,
    "sightseeing": ActivityType.CULTURE,
    "shopping": ActivityType.LEISURE,
    "nightlife": ActivityType.LEISURE,
    "relaxation": ActivityType.LEISURE,
    "spa": ActivityType.LEISURE,
    "museum": ActivityType.CULTURE,
    "tour": ActivityType.CULTURE,
    "restaurant": ActivityType.FOOD,
    "dining": ActivityType.FOOD,
    "hotel": ActivityType.ACCOMMODATION,
    "flight": ActivityType.TRANSPORT,
    "travel": ActivityType.TRANSPORT,
}


def _parse_activity_type(raw_type: str) -> ActivityType:
    try:
        return ActivityType(raw_type)
    except ValueError:
        fallback = ACTIVITY_TYPE_FALLBACKS.get(raw_type.lower())
        if fallback:
            return fallback
        # Último recurso: tipo neutro para no descartar el itinerario completo.
        return ActivityType.LEISURE


class GroqLLMService(LLMService):
    """
    Implementación del puerto LLMService usando la API de Groq,
    compatible con el SDK de OpenAI (base_url apuntando a api.groq.com).
    """

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
        )
        self._model = settings.GROQ_MODEL

    async def generate_itinerary(
        self,
        preferences: TravelPreferences,
        context_chunks: list[str],
        avoid_previous: bool = False,
    ) -> Itinerary:
        user_prompt = build_user_prompt(preferences, context_chunks, avoid_previous)
        raw = await self._complete(user_prompt)
        return self._parse_itinerary(raw, preferences)

    async def refine_itinerary(self, itinerary: Itinerary, instruction: str) -> Itinerary:
        user_prompt = build_refine_prompt(itinerary, instruction)
        raw = await self._complete(user_prompt)
        return self._parse_itinerary(raw, itinerary.preferences)

    async def _complete(self, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    @staticmethod
    def _parse_itinerary(raw: str, preferences: TravelPreferences) -> Itinerary:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Respuesta del LLM no es JSON válido: {e}\nRaw: {raw[:500]}")

        days = [
            DayPlan(
                day=d["day"],
                title=d["title"],
                theme=d["theme"],
                daily_budget=float(d["dailyBudget"]),
                activities=[
                    Activity(
                        time=a["time"],
                        title=a["title"],
                        description=a["description"],
                        type=_parse_activity_type(a["type"]),
                        cost=float(a["cost"]),
                        tip=a.get("tip"),
                    )
                    for a in d["activities"]
                ],
            )
            for d in data["days"]
        ]

        practical = data["practicalInfo"]

        return Itinerary(
            id=None,
            user_id=None,
            destination=data["destination"],
            total_days=int(data["totalDays"]),
            total_estimated_cost=float(data["totalEstimatedCost"]),
            summary=data["summary"],
            highlights=data.get("highlights", []),
            days=days,
            practical_info=PracticalInfo(
                best_time_to_visit=practical["bestTimeToVisit"],
                currency=practical["currency"],
                language=practical["language"],
                transportation=practical["transportation"],
                accommodation=practical["accommodation"],
            ),
            preferences=preferences,
        )
