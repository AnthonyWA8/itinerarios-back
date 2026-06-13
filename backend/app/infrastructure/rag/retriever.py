import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.itinerary import TravelPreferences
from app.domain.services.rag_service import RAGService
from app.infrastructure.rag.document_chunk_model import DocumentChunkModel
from app.infrastructure.rag.embedding_service import EmbeddingService


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SimpleRAGService(RAGService):
    """
    Implementación simple de RAG: filtra chunks por destino y ordena por
    similitud coseno calculada en Python (suficiente para volúmenes pequeños
    de documentos de viaje). Para producción a gran escala, migrar a pgvector.
    """

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self._session = session
        self._embeddings = embedding_service

    async def retrieve_context(self, preferences: TravelPreferences, top_k: int = 5) -> list[str]:
        destination_key = preferences.destination.split(",")[0].strip()

        stmt = select(DocumentChunkModel).where(
            DocumentChunkModel.destination.ilike(f"%{destination_key}%")
        )
        result = await self._session.execute(stmt)
        chunks = result.scalars().all()
        if not chunks:
            return []

        query_text = (
            f"{preferences.destination} - intereses: {', '.join(preferences.interests)} "
            f"- estilo: {preferences.travel_style} - restricciones: {preferences.restrictions}"
        )
        query_embedding = self._embeddings.embed(query_text)

        scored = [
            (chunk, _cosine_similarity(query_embedding, chunk.embedding))
            for chunk in chunks
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_chunks = scored[:top_k]

        return [f"[{c.source}] {c.content}" for c, _ in top_chunks]
