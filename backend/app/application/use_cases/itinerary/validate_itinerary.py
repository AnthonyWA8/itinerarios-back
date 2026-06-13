from app.domain.entities.itinerary import Itinerary, TravelPreferences


class ItineraryValidationError(Exception):
    pass


class ItineraryValidator:
    """
    Reglas de control de calidad sobre el itinerario generado por el LLM:
    - Estructura coherente (días = duración solicitada)
    - Presupuesto dentro de un rango razonable respecto al solicitado
    - Sin horarios duplicados/solapados dentro de un mismo día
    - Sin actividades vacías
    """

    BUDGET_TOLERANCE = 0.35  # +/- 35% de margen aceptable

    def validate(self, itinerary: Itinerary, preferences: TravelPreferences) -> None:
        self._validate_day_count(itinerary, preferences)
        self._validate_budget(itinerary, preferences)
        self._validate_activities(itinerary)
        self._validate_no_duplicate_times(itinerary)

    def _validate_day_count(self, itinerary: Itinerary, preferences: TravelPreferences) -> None:
        if len(itinerary.days) != preferences.duration:
            raise ItineraryValidationError(
                f"Número de días generado ({len(itinerary.days)}) "
                f"no coincide con la duración solicitada ({preferences.duration})."
            )

    def _validate_budget(self, itinerary: Itinerary, preferences: TravelPreferences) -> None:
        lower = preferences.budget * (1 - self.BUDGET_TOLERANCE)
        upper = preferences.budget * (1 + self.BUDGET_TOLERANCE)
        if not (lower <= itinerary.total_estimated_cost <= upper):
            raise ItineraryValidationError(
                f"Costo total estimado ({itinerary.total_estimated_cost}) "
                f"fuera del rango aceptable [{lower:.0f}, {upper:.0f}] "
                f"para presupuesto solicitado ({preferences.budget})."
            )

    def _validate_activities(self, itinerary: Itinerary) -> None:
        for day in itinerary.days:
            if not day.activities:
                raise ItineraryValidationError(f"Día {day.day} no tiene actividades.")
            for activity in day.activities:
                if not activity.title.strip() or not activity.description.strip():
                    raise ItineraryValidationError(
                        f"Actividad incompleta en día {day.day}."
                    )

    def _validate_no_duplicate_times(self, itinerary: Itinerary) -> None:
        for day in itinerary.days:
            times = [a.time for a in day.activities]
            if len(times) != len(set(times)):
                raise ItineraryValidationError(
                    f"Horarios duplicados en día {day.day}."
                )
