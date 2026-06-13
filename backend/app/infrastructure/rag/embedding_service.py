from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:
    """Genera embeddings localmente (gratis, sin depender del LLM)."""

    def __init__(self):
        self._model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()
