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
        # NOTA: no se usa response_format={"type": "json_object"} porque los
        # modelos de razonamiento (gpt-oss, tras retirar Llama de Groq) fallan
        # con ese modo estricto (error 400 json_validate_failed). En su lugar se
        # pide el JSON por prompt y se extrae de forma tolerante en _extract_json.
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content

    @staticmethod
    def _extract_json(raw: str) -> str:
        """
        Extrae el primer objeto JSON balanceado { ... } de la respuesta del LLM.
        Tolera texto de razonamiento antes/después y bloques markdown ```json.
        """
        if raw is None:
            raise ValueError("El LLM devolvio una respuesta vacia (None).")
        text = raw.strip()
        # Quita vallas de codigo markdown si las hubiera.
        if "```" in text:
            text = text.replace("```json", "```")
            parts = text.split("```")
            # Nos quedamos con el fragmento que contenga una llave de apertura.
            for part in parts:
                if "{" in part:
                    text = part
                    break
        start = text.find("{")
        if start == -1:
            raise ValueError(f"El LLM no devolvio JSON. Salida: {raw[:500]}")
        depth = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        raise ValueError(f"JSON incompleto/truncado en la salida del LLM: {raw[:500]}")

    @classmethod
    def _parse_itinerary(cls, raw: str, preferences: TravelPreferences) -> Itinerary:
        try:
            data = json.loads(cls._extract_json(raw))
        except json.JSONDecodeError as e:
            raise ValueError(f"Respuesta del LLM no es JSON válido: {e}\nRaw: {raw[:500]}")

        # --- Normalizacion de la estructura ---
        # Distintos modelos (p. ej. gpt-oss tras retirar Llama de Groq) a veces
        # envuelven el itinerario o devuelven listas donde esperamos objetos.
        # Desenvolvemos los casos comunes para que el parser sea robusto.
        if isinstance(data, list):
            # El modelo devolvio una lista en el nivel superior -> tomamos el 1er objeto.
            data = data[0] if data else {}
        if isinstance(data, dict) and "days" not in data:
            # El itinerario viene envuelto bajo una clave: {"itinerary": {...}}, etc.
            for wrapper_key in ("itinerary", "plan", "result", "data", "response"):
                inner = data.get(wrapper_key)
                if isinstance(inner, dict) and "days" in inner:
                    data = inner
                    break
        if not isinstance(data, dict):
            raise ValueError(
                f"Estructura inesperada del LLM (se esperaba un objeto). "
                f"Tipo recibido: {type(data).__name__}. Raw: {raw[:500]}"
            )
        if "days" not in data:
            raise ValueError(
                f"El JSON del LLM no contiene 'days'. Claves recibidas: "
                f"{list(data.keys())}. Raw: {raw[:500]}"
            )

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

        practical = data.get("practicalInfo") or {}
        if isinstance(practical, list):
            practical = practical[0] if practical else {}

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
                best_time_to_visit=practical.get("bestTimeToVisit", ""),
                currency=practical.get("currency", ""),
                language=practical.get("language", ""),
                transportation=practical.get("transportation", ""),
                accommodation=practical.get("accommodation", ""),
            ),
            preferences=preferences,
        )