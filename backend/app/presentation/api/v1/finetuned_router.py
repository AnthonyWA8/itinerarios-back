"""
Endpoint de demostración para el punto 5 (fine-tuning).

Aislado del flujo principal: usa el modelo local TinyLlama + LoRA en vez de
Groq. La inferencia en CPU es lenta (1-3 min) y la calidad/consistencia del
JSON puede ser menor que con Groq, dado el tamaño del modelo y del dataset
de fine-tuning. Se expone como evidencia de la integración real del
adaptador entrenado.
"""
from fastapi import APIRouter, HTTPException, status

from app.application.dto.itinerary_dto import GenerateItineraryRequest, ItineraryDTO
from app.infrastructure.llm.local_lora_client import LocalLoraLLMService
from app.presentation.api.v1.mappers import (
    itinerary_entity_to_dto,
    preferences_dto_to_entity,
)

router = APIRouter(prefix="/api/v1/itineraries", tags=["itineraries-finetuned"])

_local_service = LocalLoraLLMService()


@router.post("/generate-finetuned", response_model=ItineraryDTO)
async def generate_with_finetuned_model(payload: GenerateItineraryRequest):
    preferences = preferences_dto_to_entity(payload.preferences)
    try:
        itinerary = _local_service.generate_itinerary(preferences)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return itinerary_entity_to_dto(itinerary)
