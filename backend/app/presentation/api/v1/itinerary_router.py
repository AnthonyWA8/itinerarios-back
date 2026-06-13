from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.itinerary_dto import (
    GenerateItineraryRequest,
    ItineraryDTO,
    RefineItineraryRequest,
    SaveItineraryRequest,
)
from app.application.use_cases.itinerary.generate_itinerary import GenerateItineraryUseCase
from app.application.use_cases.itinerary.regenerate_itinerary import RegenerateItineraryUseCase
from app.application.use_cases.itinerary.refine_itinerary import RefineItineraryUseCase
from app.application.use_cases.itinerary.save_itinerary import SaveItineraryUseCase
from app.application.use_cases.itinerary.get_user_itineraries import (
    DeleteItineraryUseCase,
    GetUserItinerariesUseCase,
)
from app.presentation.api.dependencies import (
    get_current_user_id,
    get_delete_itinerary_use_case,
    get_generate_itinerary_use_case,
    get_optional_user_id,
    get_refine_itinerary_use_case,
    get_regenerate_itinerary_use_case,
    get_save_itinerary_use_case,
    get_user_itineraries_use_case,
)
from app.presentation.api.v1.mappers import (
    itinerary_entity_to_dto,
    preferences_dto_to_entity,
)

router = APIRouter(prefix="/api/v1/itineraries", tags=["itineraries"])


@router.post("/generate", response_model=ItineraryDTO)
async def generate_itinerary(
    payload: GenerateItineraryRequest,
    use_case: Annotated[GenerateItineraryUseCase, Depends(get_generate_itinerary_use_case)],
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
):
    preferences = preferences_dto_to_entity(payload.preferences)
    try:
        itinerary = await use_case.execute(preferences, user_id=user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return itinerary_entity_to_dto(itinerary)


@router.post("/regenerate", response_model=ItineraryDTO)
async def regenerate_itinerary(
    payload: GenerateItineraryRequest,
    use_case: Annotated[RegenerateItineraryUseCase, Depends(get_regenerate_itinerary_use_case)],
    user_id: Annotated[UUID | None, Depends(get_optional_user_id)],
):
    preferences = preferences_dto_to_entity(payload.preferences)
    try:
        itinerary = await use_case.execute(preferences, user_id=user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return itinerary_entity_to_dto(itinerary)


@router.post("/refine", response_model=ItineraryDTO)
async def refine_itinerary(
    payload: RefineItineraryRequest,
    use_case: Annotated[RefineItineraryUseCase, Depends(get_refine_itinerary_use_case)],
):
    try:
        itinerary = await use_case.execute(UUID(payload.itinerary_id), payload.instruction)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    return itinerary_entity_to_dto(itinerary)


@router.post("", response_model=ItineraryDTO, status_code=status.HTTP_201_CREATED)
async def save_itinerary(
    payload: SaveItineraryRequest,
    use_case: Annotated[SaveItineraryUseCase, Depends(get_save_itinerary_use_case)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    from app.presentation.api.v1.mappers import preferences_dto_to_entity
    from app.domain.entities.itinerary import (
        Activity, ActivityType, DayPlan, Itinerary, PracticalInfo,
    )

    dto = payload.itinerary
    itinerary = Itinerary(
        id=None,
        user_id=user_id,
        destination=dto.destination,
        total_days=dto.total_days,
        total_estimated_cost=dto.total_estimated_cost,
        summary=dto.summary,
        highlights=dto.highlights,
        days=[
            DayPlan(
                day=d.day,
                title=d.title,
                theme=d.theme,
                daily_budget=d.daily_budget,
                activities=[
                    Activity(
                        time=a.time,
                        title=a.title,
                        description=a.description,
                        type=ActivityType(a.type),
                        cost=a.cost,
                        tip=a.tip,
                    )
                    for a in d.activities
                ],
            )
            for d in dto.days
        ],
        practical_info=PracticalInfo(
            best_time_to_visit=dto.practical_info.best_time_to_visit,
            currency=dto.practical_info.currency,
            language=dto.practical_info.language,
            transportation=dto.practical_info.transportation,
            accommodation=dto.practical_info.accommodation,
        ),
        # Preferencias originales que generaron este itinerario (necesarias para persistencia/RAG futuro).
        preferences=preferences_dto_to_entity(payload.preferences),
        note=payload.note,
    )
    saved = await use_case.execute(itinerary, user_id, payload.note)
    return itinerary_entity_to_dto(saved)


@router.get("", response_model=list[ItineraryDTO])
async def get_my_itineraries(
    use_case: Annotated[GetUserItinerariesUseCase, Depends(get_user_itineraries_use_case)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    itineraries = await use_case.execute(user_id)
    return [itinerary_entity_to_dto(i) for i in itineraries]


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary(
    itinerary_id: UUID,
    use_case: Annotated[DeleteItineraryUseCase, Depends(get_delete_itinerary_use_case)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    await use_case.execute(itinerary_id, user_id)
