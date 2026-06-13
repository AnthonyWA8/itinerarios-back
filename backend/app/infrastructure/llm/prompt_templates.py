"""
Plantillas de prompting para la generación de itinerarios.

Técnicas aplicadas:
- System prompt con rol fijo y reglas de salida estrictas (JSON schema).
- Few-shot: se inyecta un ejemplo de itinerario bien formado.
- Contexto RAG: fragmentos recuperados se insertan como "información verificada".
- Instrucciones de coherencia presupuestal y de horarios (apoya el validador).
"""

from app.domain.entities.itinerary import Itinerary, TravelPreferences

ITINERARY_JSON_SCHEMA_DESCRIPTION = """
Debes responder ÚNICAMENTE con un objeto JSON (sin texto adicional, sin markdown) con esta forma exacta:

{
  "destination": string,
  "totalDays": number,
  "totalEstimatedCost": number,
  "summary": string,
  "highlights": string[] (máximo 4),
  "days": [
    {
      "day": number,
      "title": string,
      "theme": string,
      "dailyBudget": number,
      "activities": [
        {
          "time": "HH:MM",
          "title": string,
          "description": string,
          "type": "food" | "culture" | "outdoor" | "leisure" | "transport" | "accommodation",
          "cost": number,
          "tip": string (opcional)
        }
      ]
    }
  ],
  "practicalInfo": {
    "bestTimeToVisit": string,
    "currency": string,
    "language": string,
    "transportation": string,
    "accommodation": string
  }
}
"""

FEW_SHOT_EXAMPLE = """
Ejemplo de un día bien formado (para 1 día de un itinerario de Tokio, presupuesto moderado):

{
  "day": 1,
  "title": "Día 1: Llegada y primeras impresiones",
  "theme": "Llegada y primeras impresiones",
  "dailyBudget": 150,
  "activities": [
    {"time": "14:00", "title": "Check-in y orientación", "description": "Llegada al hotel en Shinjuku, descanso breve y familiarización con el barrio.", "type": "accommodation", "cost": 60},
    {"time": "16:30", "title": "Cruce de Shibuya", "description": "Primera inmersión en la energía de Tokio, observando el icónico cruce peatonal.", "type": "culture", "cost": 0, "tip": "Sube al Starbucks del segundo piso para la mejor vista."},
    {"time": "19:30", "title": "Cena de bienvenida en izakaya", "description": "Cena tradicional japonesa en un izakaya local de Shibuya.", "type": "food", "cost": 35, "tip": "Pide el menú degustación si está disponible."}
  ]
}
"""

SYSTEM_PROMPT = f"""Eres un planificador de viajes experto con años de experiencia diseñando itinerarios personalizados, realistas y atractivos.

Reglas obligatorias:
1. Genera EXACTAMENTE el número de días solicitado (totalDays = duration).
2. El campo "totalEstimatedCost" debe ser la suma de los "dailyBudget" de todos los días, y debe estar dentro de un 35% del presupuesto total indicado por el usuario.
3. Cada día debe tener al menos 3 actividades, con horarios (time) ÚNICOS dentro del día y ordenados cronológicamente.
4. Las actividades deben respetar las restricciones indicadas por el usuario (dietéticas, movilidad, etc.).
5. Usa el "Contexto verificado" provisto (si existe) para incluir lugares, datos prácticos y recomendaciones reales y específicas del destino, en lugar de información genérica.
6. El idioma de salida debe ser español.
7. No incluyas contenido sesgado, discriminatorio ni inapropiado. Mantén un tono profesional, inclusivo y positivo.
8. Responde ÚNICAMENTE con el JSON solicitado, sin explicaciones, sin markdown, sin backticks.

{ITINERARY_JSON_SCHEMA_DESCRIPTION}

{FEW_SHOT_EXAMPLE}
"""


def build_user_prompt(
    preferences: TravelPreferences,
    context_chunks: list[str],
    avoid_previous: bool = False,
) -> str:
    interests_str = ", ".join(preferences.interests)
    context_block = ""
    if context_chunks:
        joined = "\n---\n".join(context_chunks)
        context_block = f"\nContexto verificado sobre el destino (guías/reseñas reales):\n{joined}\n"

    avoid_block = ""
    if avoid_previous:
        avoid_block = (
            "\nEl usuario solicitó regenerar el itinerario: genera una propuesta "
            "DIFERENTE a una anterior, variando actividades, horarios y lugares "
            "destacados, manteniendo la misma calidad y coherencia.\n"
        )

    return f"""Genera un itinerario de viaje con las siguientes preferencias:

- Destino: {preferences.destination}
- Duración: {preferences.duration} días
- Presupuesto total: {preferences.budget} USD ({preferences.budget_type})
- Intereses: {interests_str}
- Tipo de viajero: {preferences.group_type}
- Ritmo del viaje: {preferences.travel_style}
- Restricciones/requisitos especiales: {preferences.restrictions or "Ninguna"}
{context_block}{avoid_block}
Recuerda: responde solo el JSON, respetando exactamente el schema indicado."""


def build_refine_prompt(itinerary: Itinerary, instruction: str) -> str:
    import json

    current = {
        "destination": itinerary.destination,
        "totalDays": itinerary.total_days,
        "totalEstimatedCost": itinerary.total_estimated_cost,
        "summary": itinerary.summary,
        "highlights": itinerary.highlights,
        "days": [
            {
                "day": d.day,
                "title": d.title,
                "theme": d.theme,
                "dailyBudget": d.daily_budget,
                "activities": [
                    {
                        "time": a.time,
                        "title": a.title,
                        "description": a.description,
                        "type": a.type.value if hasattr(a.type, "value") else a.type,
                        "cost": a.cost,
                        **({"tip": a.tip} if a.tip else {}),
                    }
                    for a in d.activities
                ],
            }
            for d in itinerary.days
        ],
        "practicalInfo": {
            "bestTimeToVisit": itinerary.practical_info.best_time_to_visit,
            "currency": itinerary.practical_info.currency,
            "language": itinerary.practical_info.language,
            "transportation": itinerary.practical_info.transportation,
            "accommodation": itinerary.practical_info.accommodation,
        },
    }

    return f"""Aquí está el itinerario actual en formato JSON:

{json.dumps(current, ensure_ascii=False, indent=2)}

El usuario solicita el siguiente cambio:
"{instruction}"

Genera una versión ACTUALIZADA del itinerario completo aplicando ese cambio,
manteniendo el mismo número de días ({itinerary.total_days}) y respetando el
mismo schema JSON indicado en las instrucciones del sistema. Responde solo el JSON."""
