"""
Script de ingesta RAG: pobla document_chunks con información curada de
destinos populares (guías, consejos prácticos, recomendaciones locales).

Uso:
    python -m scripts.seed_rag
"""
import asyncio
import uuid

from app.infrastructure.database.session import Base, engine, async_session_factory
from app.infrastructure.rag.document_chunk_model import DocumentChunkModel
from app.infrastructure.rag.embedding_service import EmbeddingService
from app.infrastructure.database.models import user_model, itinerary_model, feedback_model  # noqa: F401

DESTINATIONS_DATA = {
    "Tokio": [
        ("Wikivoyage", "Tokio es una ciudad masiva pero muy bien organizada para turistas. El metro es la forma más eficiente de moverse; compra una tarjeta Suica o Pasmo al llegar. Los barrios de Shibuya y Shinjuku son ideales para vida nocturna y compras, mientras que Asakusa conserva el Tokio tradicional con el templo Senso-ji."),
        ("Guía gastronómica", "Para experiencias culinarias auténticas, visita el mercado de Tsukiji exterior para desayunos de sushi fresco. Los restaurantes pequeños de ramen suelen tener fila pero la espera vale la pena. Los izakayas (tabernas) en callejones como Omoide Yokocho ofrecen ambiente local genuino."),
        ("Reseña de viajero", "Recomiendo reservar al menos medio día para Akihabara si te interesa la cultura otaku y tecnología, y otro medio día para un parque como Ueno o Yoyogi si buscas naturaleza dentro de la ciudad."),
        ("Información práctica", "La mejor época para visitar Tokio es primavera (marzo-mayo) por los cerezos en flor, u otoño (octubre-noviembre) por el clima agradable. El verano es muy caluroso y húmedo. El idioma local es japonés; en zonas turísticas hay señalización en inglés."),
    ],
    "París": [
        ("Wikivoyage", "París se organiza en 20 distritos (arrondissements) en espiral desde el centro. El metro es extenso y económico; un pase de varios días ahorra tiempo. El Louvre, Notre-Dame y la Torre Eiffel son imprescindibles pero conviene reservar entradas con anticipación para evitar largas filas."),
        ("Guía gastronómica", "Para una experiencia culinaria auténtica, los mercados como el de la rue Mouffetard ofrecen quesos, panes y vinos locales. Los bistrós de barrio suelen ser más auténticos y económicos que los restaurantes turísticos cerca de monumentos principales."),
        ("Reseña de viajero", "El barrio de Montmartre es perfecto para una tarde de paseo, con vistas panorámicas desde Sacré-Cœur y ambiente artístico. Para experiencias culturales, el Musée d'Orsay suele tener menos aglomeración que el Louvre."),
        ("Información práctica", "La mejor época es primavera u otoño, evitando el calor del verano y las multitudes de agosto. El idioma es francés; aprender frases básicas de cortesía es muy apreciado por los locales."),
    ],
    "Cartagena": [
        ("Wikivoyage", "Cartagena de Indias combina playas caribeñas con un centro histórico amurallado declarado Patrimonio de la Humanidad. La Ciudad Amurallada es ideal para caminar, especialmente al atardecer cuando baja el calor."),
        ("Guía gastronómica", "La gastronomía local incluye arepas de huevo, ceviche de camarón y cocadas. El Mercado de Bazurto ofrece una experiencia auténtica y económica, aunque puede ser intenso para visitantes primerizos."),
        ("Reseña de viajero", "Las Islas del Rosario son una excursión de día popular para actividades al aire libre y snorkel, aunque conviene reservar con operadores confiables. Getsemaní es un barrio vibrante con arte urbano y buena vida nocturna."),
        ("Información práctica", "El clima es cálido y húmedo todo el año, con temporada de lluvias entre abril-mayo y octubre-noviembre. El idioma es español. Se recomienda protección solar y mucha hidratación."),
    ],
}


async def seed():
    embedding_service = EmbeddingService()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        for destination, chunks in DESTINATIONS_DATA.items():
            for source, content in chunks:
                embedding = embedding_service.embed(content)
                session.add(
                    DocumentChunkModel(
                        id=uuid.uuid4(),
                        destination=destination,
                        source=source,
                        content=content,
                        embedding=embedding,
                    )
                )
        await session.commit()

    print("RAG seed completado.")


if __name__ == "__main__":
    asyncio.run(seed())
