from app.core.config import settings


class EmbeddingService:
    """Genera embeddings localmente (gratis, sin depender del LLM).

    Carga el modelo de forma diferida (lazy) la primera vez que se usa,
    para no consumir memoria durante el arranque del servidor.
    """

    def __init__(self):
        self._model = None

    def _ensure_loaded(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed(self, text: str) -> list[float]:
        self._ensure_loaded()
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._ensure_loaded()
        return self._model.encode(texts, normalize_embeddings=True).tolist()
