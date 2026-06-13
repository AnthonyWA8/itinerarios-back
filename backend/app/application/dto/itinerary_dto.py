from typing import Literal, Optional

from pydantic import BaseModel, Field


class TravelPreferencesDTO(BaseModel):
    destination: str
    duration: int = Field(ge=1, le=21)
    budget: float = Field(ge=200, le=10000)
    budget_type: Literal["budget", "moderate", "luxury"] = Field(alias="budgetType")
    interests: list[str]
    restrictions: str = ""
    travel_style: str = Field(alias="travelStyle")
    group_type: str = Field(alias="groupType")

    class Config:
        populate_by_name = True


class ActivityDTO(BaseModel):
    time: str
    title: str
    description: str
    type: Literal["food", "culture", "outdoor", "leisure", "transport", "accommodation"]
    cost: float
    tip: Optional[str] = None


class DayPlanDTO(BaseModel):
    day: int
    title: str
    theme: str
    activities: list[ActivityDTO]
    daily_budget: float = Field(serialization_alias="dailyBudget")


class PracticalInfoDTO(BaseModel):
    best_time_to_visit: str = Field(serialization_alias="bestTimeToVisit")
    currency: str
    language: str
    transportation: str
    accommodation: str


class ItineraryDTO(BaseModel):
    id: Optional[str] = None
    destination: str
    total_days: int = Field(serialization_alias="totalDays")
    total_estimated_cost: float = Field(serialization_alias="totalEstimatedCost")
    summary: str
    highlights: list[str]
    days: list[DayPlanDTO]
    practical_info: PracticalInfoDTO = Field(serialization_alias="practicalInfo")

    class Config:
        populate_by_name = True


class GenerateItineraryRequest(BaseModel):
    preferences: TravelPreferencesDTO


class RefineItineraryRequest(BaseModel):
    itinerary_id: str
    instruction: str


class SaveItineraryRequest(BaseModel):
    itinerary: ItineraryDTO
    preferences: TravelPreferencesDTO
    note: Optional[str] = None
