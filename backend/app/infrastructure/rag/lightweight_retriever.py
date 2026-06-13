from app.domain.entities.itinerary import TravelPreferences
from app.domain.services.rag_service import RAGService

# Fragmentos curados (sin embeddings) para mantener RAG funcional con bajo consumo
# de memoria en entornos con recursos limitados (ej. Render free tier).
STATIC_CONTEXT: dict[str, list[str]] = {
    "Tokio": [
        "[Wikivoyage] Tokio es una ciudad masiva pero muy bien organizada para turistas. El metro es la forma más eficiente de moverse; compra una tarjeta Suica o Pasmo al llegar.",
        "[Guía gastronómica] Para experiencias culinarias auténticas, visita el mercado de Tsukiji exterior para desayunos de sushi fresco. Los izakayas en callejones como Omoide Yokocho ofrecen ambiente local genuino.",
    ],
    "París": [
        "[Wikivoyage] París se organiza en 20 distritos (arrondissements) en espiral desde el centro. El metro es extenso y económico; un pase de varios días ahorra tiempo.",
        "[Guía gastronómica] Los bistrós de barrio suelen ser más auténticos y económicos que los restaurantes turísticos cerca de monumentos principales.",
    ],
    "Cartagena": [
        "[Wikivoyage] Cartagena de Indias combina playas caribeñas con un centro histórico amurallado declarado Patrimonio de la Humanidad.",
        "[Reseña de viajero] Las Islas del Rosario son una excursión de día popular para actividades al aire libre y snorkel.",
    ],
}


class LightweightRAGService(RAGService):
    """
    Implementación de RAG sin dependencias pesadas (sin sentence-transformers):
    devuelve fragmentos curados según coincidencia simple de texto con el destino.

    Pensada para entornos con memoria limitada (ej. Render free tier - 512MB).
    Para RAG con embeddings y similitud semántica, usar SimpleRAGService
    (requiere sentence-transformers) en entornos con más recursos.
    """

    async def retrieve_context(self, preferences: TravelPreferences, top_k: int = 5) -> list[str]:
        destination_key = preferences.destination.split(",")[0].strip().lower()
        for key, chunks in STATIC_CONTEXT.items():
            if key.lower() in destination_key or destination_key in key.lower():
                return chunks[:top_k]
        return []
