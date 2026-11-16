from app.application.dto.itinerary_dto import (
    ActivityDTO,
    LocationDTO,
    DayPlanDTO,
    ItineraryDTO,
    PracticalInfoDTO,
    TravelPreferencesDTO,
)
from app.domain.entities.itinerary import (
    BudgetType,
    Itinerary,
    PlaceLocation,
    TravelPreferences,
)


def location_entity_to_dto(loc: PlaceLocation | None) -> LocationDTO | None:
    if loc is None:
        return None
    return LocationDTO(
        name=loc.name,
        address=loc.address,
        lat=loc.latitude,
        lng=loc.longitude,
        url=loc.url,
        rating=loc.rating,
        source=loc.source,
        verified=loc.verified,
    )


def location_dto_to_entity(dto: LocationDTO | None) -> PlaceLocation | None:
    if dto is None:
        return None
    return PlaceLocation(
        name=dto.name,
        address=dto.address,
        latitude=dto.lat,
        longitude=dto.lng,
        url=dto.url,
        rating=dto.rating,
        source=dto.source,
        verified=dto.verified,
    )


def preferences_dto_to_entity(dto: TravelPreferencesDTO) -> TravelPreferences:
    return TravelPreferences(
        destination=dto.destination,
        duration=dto.duration,
        budget=dto.budget,
        budget_type=BudgetType(dto.budget_type),
        interests=dto.interests,
        restrictions=dto.restrictions,
        travel_style=dto.travel_style,
        group_type=dto.group_type,
    )


def itinerary_entity_to_dto(itinerary: Itinerary) -> ItineraryDTO:
    return ItineraryDTO(
        id=str(itinerary.id) if itinerary.id else None,
        destination=itinerary.destination,
        total_days=itinerary.total_days,
        total_estimated_cost=itinerary.total_estimated_cost,
        summary=itinerary.summary,
        highlights=itinerary.highlights,
        days=[
            DayPlanDTO(
                day=d.day,
                title=d.title,
                theme=d.theme,
                daily_budget=d.daily_budget,
                activities=[
                    ActivityDTO(
                        time=a.time,
                        title=a.title,
                        description=a.description,
                        type=a.type.value if hasattr(a.type, "value") else a.type,
                        cost=a.cost,
                        tip=a.tip,
                        place=a.place,
                        location=location_entity_to_dto(a.location),
                    )
                    for a in d.activities
                ],
            )
            for d in itinerary.days
        ],
        practical_info=PracticalInfoDTO(
            best_time_to_visit=itinerary.practical_info.best_time_to_visit,
            currency=itinerary.practical_info.currency,
            language=itinerary.practical_info.language,
            transportation=itinerary.practical_info.transportation,
            accommodation=itinerary.practical_info.accommodation,
        ),
    )
