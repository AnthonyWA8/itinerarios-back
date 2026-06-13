from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.itinerary import (
    Activity,
    BudgetType,
    DayPlan,
    Itinerary,
    PracticalInfo,
    TravelPreferences,
)
from app.domain.repositories.itinerary_repository import ItineraryRepository
from app.infrastructure.database.models.itinerary_model import ItineraryModel


class SQLAlchemyItineraryRepository(ItineraryRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, itinerary: Itinerary) -> Itinerary:
        model = ItineraryModel(
            id=itinerary.id,
            user_id=itinerary.user_id,
            destination=itinerary.destination,
            total_days=itinerary.total_days,
            total_estimated_cost=itinerary.total_estimated_cost,
            summary=itinerary.summary,
            highlights=itinerary.highlights,
            days=[self._day_to_dict(d) for d in itinerary.days],
            practical_info=self._practical_info_to_dict(itinerary.practical_info),
            preferences=self._preferences_to_dict(itinerary.preferences),
            note=itinerary.note,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, itinerary_id: UUID) -> Optional[Itinerary]:
        result = await self._session.execute(
            select(ItineraryModel).where(ItineraryModel.id == itinerary_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_user(self, user_id: UUID) -> list[Itinerary]:
        result = await self._session.execute(
            select(ItineraryModel)
            .where(ItineraryModel.user_id == user_id)
            .order_by(ItineraryModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, itinerary_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(ItineraryModel).where(
                ItineraryModel.id == itinerary_id, ItineraryModel.user_id == user_id
            )
        )
        await self._session.commit()

    # ---------- Mapeo dominio <-> persistencia ----------

    @staticmethod
    def _day_to_dict(day: DayPlan) -> dict:
        return {
            "day": day.day,
            "title": day.title,
            "theme": day.theme,
            "daily_budget": day.daily_budget,
            "activities": [
                {
                    "time": a.time,
                    "title": a.title,
                    "description": a.description,
                    "type": a.type.value,
                    "cost": a.cost,
                    "tip": a.tip,
                }
                for a in day.activities
            ],
        }

    @staticmethod
    def _practical_info_to_dict(info: PracticalInfo) -> dict:
        return {
            "best_time_to_visit": info.best_time_to_visit,
            "currency": info.currency,
            "language": info.language,
            "transportation": info.transportation,
            "accommodation": info.accommodation,
        }

    @staticmethod
    def _preferences_to_dict(prefs: TravelPreferences) -> dict:
        return {
            "destination": prefs.destination,
            "duration": prefs.duration,
            "budget": prefs.budget,
            "budget_type": prefs.budget_type.value,
            "interests": prefs.interests,
            "restrictions": prefs.restrictions,
            "travel_style": prefs.travel_style,
            "group_type": prefs.group_type,
        }

    @classmethod
    def _to_entity(cls, model: ItineraryModel) -> Itinerary:
        prefs_dict = model.preferences
        days = [
            DayPlan(
                day=d["day"],
                title=d["title"],
                theme=d["theme"],
                daily_budget=d["daily_budget"],
                activities=[
                    Activity(
                        time=a["time"],
                        title=a["title"],
                        description=a["description"],
                        type=a["type"],
                        cost=a["cost"],
                        tip=a.get("tip"),
                    )
                    for a in d["activities"]
                ],
            )
            for d in model.days
        ]
        info_dict = model.practical_info
        return Itinerary(
            id=model.id,
            user_id=model.user_id,
            destination=model.destination,
            total_days=model.total_days,
            total_estimated_cost=model.total_estimated_cost,
            summary=model.summary,
            highlights=model.highlights,
            days=days,
            practical_info=PracticalInfo(
                best_time_to_visit=info_dict["best_time_to_visit"],
                currency=info_dict["currency"],
                language=info_dict["language"],
                transportation=info_dict["transportation"],
                accommodation=info_dict["accommodation"],
            ),
            preferences=TravelPreferences(
                destination=prefs_dict["destination"],
                duration=prefs_dict["duration"],
                budget=prefs_dict["budget"],
                budget_type=BudgetType(prefs_dict["budget_type"]),
                interests=prefs_dict["interests"],
                restrictions=prefs_dict["restrictions"],
                travel_style=prefs_dict["travel_style"],
                group_type=prefs_dict["group_type"],
            ),
            note=model.note,
            created_at=model.created_at,
        )
