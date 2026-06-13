"""
Reward model heurístico para evaluar la calidad de un itinerario generado.

Esta es la pieza central de la técnica RL aplicada (punto 6 del enunciado):
en lugar de PPO completo (inviable en el tiempo disponible), se implementa
"Best-of-N sampling" / rejection sampling guiado por reward: se generan N
candidatos y se selecciona el de mayor puntaje según este modelo de reward.

El score combina:
- Ajuste al presupuesto solicitado (más cerca = mejor)
- Diversidad de tipos de actividad (evita itinerarios monótonos)
- Completitud informativa (presencia de "tips" útiles)
- Densidad de actividades por día (ni muy vacío ni saturado)
- Bonus por feedback histórico positivo en destinos similares (RLHF-lite)
"""

from collections import Counter

from app.domain.entities.itinerary import Itinerary, TravelPreferences


class ItineraryRewardModel:

    IDEAL_ACTIVITIES_PER_DAY = (3, 5)  # rango ideal (min, max)

    def score(
        self,
        itinerary: Itinerary,
        preferences: TravelPreferences,
        historical_avg_rating: float | None = None,
    ) -> float:
        budget_score = self._budget_fit_score(itinerary, preferences)
        diversity_score = self._activity_diversity_score(itinerary)
        completeness_score = self._tips_completeness_score(itinerary)
        density_score = self._activity_density_score(itinerary)
        feedback_score = self._feedback_score(historical_avg_rating)

        # Pesos: el ajuste presupuestal y la diversidad son los más importantes.
        total = (
            0.35 * budget_score
            + 0.25 * diversity_score
            + 0.15 * completeness_score
            + 0.15 * density_score
            + 0.10 * feedback_score
        )
        return round(total, 4)

    def _budget_fit_score(self, itinerary: Itinerary, preferences: TravelPreferences) -> float:
        if preferences.budget <= 0:
            return 0.5
        diff_ratio = abs(itinerary.total_estimated_cost - preferences.budget) / preferences.budget
        # 0% de diferencia -> score 1.0; 35% de diferencia (límite del validador) -> score 0.0
        score = max(0.0, 1.0 - diff_ratio / 0.35)
        return min(1.0, score)

    def _activity_diversity_score(self, itinerary: Itinerary) -> float:
        all_types = [a.type for day in itinerary.days for a in day.activities]
        if not all_types:
            return 0.0
        counts = Counter(all_types)
        unique_types = len(counts)
        total = len(all_types)
        # Penaliza si un solo tipo domina demasiado (ej. todo "food")
        max_share = max(counts.values()) / total
        balance_score = 1.0 - max(0.0, max_share - 0.5)  # penaliza si >50% es un solo tipo
        coverage_score = min(1.0, unique_types / 4)  # ideal: al menos 4 tipos distintos
        return round((balance_score + coverage_score) / 2, 4)

    def _tips_completeness_score(self, itinerary: Itinerary) -> float:
        all_activities = [a for day in itinerary.days for a in day.activities]
        if not all_activities:
            return 0.0
        with_tip = sum(1 for a in all_activities if a.tip and a.tip.strip())
        return round(with_tip / len(all_activities), 4)

    def _activity_density_score(self, itinerary: Itinerary) -> float:
        if not itinerary.days:
            return 0.0
        scores = []
        low, high = self.IDEAL_ACTIVITIES_PER_DAY
        for day in itinerary.days:
            n = len(day.activities)
            if low <= n <= high:
                scores.append(1.0)
            elif n < low:
                scores.append(max(0.0, n / low))
            else:
                scores.append(max(0.0, 1.0 - (n - high) * 0.2))
        return round(sum(scores) / len(scores), 4)

    def _feedback_score(self, historical_avg_rating: float | None) -> float:
        if historical_avg_rating is None:
            return 0.5  # neutral si no hay datos
        # rating 1-5 -> score 0-1
        return round(max(0.0, min(1.0, (historical_avg_rating - 1) / 4)), 4)
