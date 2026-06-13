import uuid

from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base
from app.infrastructure.database.types import GUID


class DocumentChunkModel(Base):
    """
    Chunks de guías de viaje / reseñas / info local, con su embedding,
    usados como base de conocimiento para RAG.

    El embedding se guarda como JSON (lista de floats) para compatibilidad
    con SQLite. La similitud se calcula en Python (coseno) en el retriever.
    Para producción con PostgreSQL + pgvector, se puede migrar este campo
    a tipo Vector sin cambiar la interfaz RAGService.
    """
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    destination: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
