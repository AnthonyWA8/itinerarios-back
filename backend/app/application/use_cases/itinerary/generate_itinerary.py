import asyncio
from typing import Optional
from uuid import UUID

from app.domain.entities.itinerary import Itinerary, TravelPreferences
from app.domain.repositories.feedback_repository import FeedbackRepository
from app.domain.services.llm_service import LLMService
from app.domain.services.rag_service import RAGService
from app.application.use_cases.itinerary.reward_model import ItineraryRewardModel
from app.application.use_cases.itinerary.validate_itinerary import (
    ItineraryValidator,
    ItineraryValidationError,
)


class GenerateItineraryUseCase:
    """
    Orquesta:
      1. RAG: recupera contexto relevante (guías, reseñas) según preferencias.
      2. LLM: genera N itinerarios candidatos en paralelo (prompting guiado + contexto).
      3. Validación: descarta candidatos que no pasen control de calidad.
      4. Reward model (RL - best-of-N / rejection sampling): puntúa los candidatos
         válidos y selecciona el de mayor reward, considerando también feedback
         histórico de usuarios para destinos similares (RLHF-lite).
    """

    MAX_RETRIES = 2
    N_CANDIDATES = 2  # número de itinerarios generados en paralelo para best-of-N

    def __init__(
        self,
        llm_service: LLMService,
        rag_service: RAGService,
        validator: ItineraryValidator,
        reward_model: ItineraryRewardModel,
        feedback_repository: FeedbackRepository,
    ):
        self._llm = llm_service
        self._rag = rag_service
        self._validator = validator
        self._reward_model = reward_model
        self._feedback = feedback_repository

    async def execute(
        self,
        preferences: TravelPreferences,
        user_id: Optional[UUID] = None,
    ) -> Itinerary:
        context_chunks = await self._rag.retrieve_context(preferences, top_k=5)
        historical_rating = await self._feedback.get_average_rating_for_destination(
            preferences.destination
        )

        valid_candidates: list[Itinerary] = []
        last_error: Optional[str] = None

        for attempt in range(self.MAX_RETRIES + 1):
            candidates = await asyncio.gather(
                *[
                    self._llm.generate_itinerary(
                        preferences=preferences,
                        context_chunks=context_chunks,
                        avoid_previous=attempt > 0,
                    )
                    for _ in range(self.N_CANDIDATES)
                ],
                return_exceptions=True,
            )

            for candidate in candidates:
                if isinstance(candidate, Exception):
                    last_error = str(candidate)
                    continue
                try:
                    self._validator.validate(candidate, preferences)
                    valid_candidates.append(candidate)
                except ItineraryValidationError as e:
                    last_error = str(e)

            if valid_candidates:
                break

        if not valid_candidates:
            raise RuntimeError(
                f"No se pudo generar un itinerario válido tras {self.MAX_RETRIES + 1} intentos "
                f"(best-of-{self.N_CANDIDATES}). Último error: {last_error}"
            )

        # RL - Best-of-N: selecciona el candidato con mayor reward.
        best = max(
            valid_candidates,
            key=lambda it: self._reward_model.score(it, preferences, historical_rating),
        )
        best.user_id = user_id
        return best
