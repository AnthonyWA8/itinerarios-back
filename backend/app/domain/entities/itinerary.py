from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class ActivityType(str, Enum):
    FOOD = "food"
    CULTURE = "culture"
    OUTDOOR = "outdoor"
    LEISURE = "leisure"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"


class BudgetType(str, Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    LUXURY = "luxury"


@dataclass
class Activity:
    time: str
    title: str
    description: str
    type: ActivityType
    cost: float
    tip: Optional[str] = None


@dataclass
class DayPlan:
    day: int
    title: str
    theme: str
    activities: list[Activity]
    daily_budget: float


@dataclass
class PracticalInfo:
    best_time_to_visit: str
    currency: str
    language: str
    transportation: str
    accommodation: str


@dataclass
class TravelPreferences:
    destination: str
    duration: int
    budget: float
    budget_type: BudgetType
    interests: list[str]
    restrictions: str
    travel_style: str
    group_type: str


@dataclass
class Itinerary:
    id: Optional[UUID]
    user_id: Optional[UUID]
    destination: str
    total_days: int
    total_estimated_cost: float
    summary: str
    highlights: list[str]
    days: list[DayPlan]
    practical_info: PracticalInfo
    preferences: TravelPreferences
    created_at: Optional[datetime] = None
    note: Optional[str] = None
