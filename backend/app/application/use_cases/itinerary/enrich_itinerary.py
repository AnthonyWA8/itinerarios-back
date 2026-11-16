"""
Verificación de lugares reales mediante MCP.

Después de que el LLM genera el itinerario, este paso consulta un servidor MCP
de mapas (Google Maps Grounding Lite o el servidor propio sobre OpenStreetMap)
para comprobar que cada lugar propuesto existe y completar sus datos reales:
dirección, coordenadas y enlace al mapa.

Es tolerante a fallos: si el servidor MCP no responde o se agota el tiempo, el
itinerario se entrega igual, solo sin los datos de ubicación que falten.
"""

import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Optional

from app.domain.entities.itinerary import Activity, ActivityType, Itinerary, PlaceLocation
from app.domain.services.places_service import GeoPoint, PlaceResult, PlacesService, PlacesSession

logger = logging.getLogger(__name__)

# Tipos de actividad que no suelen ocurrir en un lugar concreto verificable.
_SKIP_TYPES = {ActivityType.TRANSPORT}


@dataclass
class EnrichmentReport:
    source: Optional[str] = None
    requested: int = 0
    verified: int = 0
    timed_out: bool = False
    error: Optional[str] = None


def _haversine_km(a: GeoPoint, lat: float, lng: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.latitude), math.radians(lat)
    dp, dl = math.radians(lat - a.latitude), math.radians(lng - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class ItineraryPlacesEnricher:
    def __init__(
        self,
        places_service: Optional[PlacesService],
        max_lookups: int = 10,
        time_budget_seconds: float = 25.0,
        max_distance_km: float = 80.0,
    ):
        self._places = places_service
        self._max_lookups = max_lookups
        self._time_budget = time_budget_seconds
        self._max_distance_km = max_distance_km

    @property
    def enabled(self) -> bool:
        return self._places is not None

    async def enrich(self, itinerary: Itinerary) -> EnrichmentReport:
        report = EnrichmentReport(source=getattr(self._places, "source", None))
        if self._places is None:
            return report

        targets = self._select_targets(itinerary)
        report.requested = len(targets)
        if not targets:
            return report

        try:
            async with asyncio.timeout(self._time_budget):
                async with self._places.session() as session:
                    center = await self._locate_destination(session, itinerary.destination)
                    await asyncio.gather(
                        *(self._verify(session, place, acts, itinerary.destination, center, report)
                          for place, acts in targets)
                    )
        except TimeoutError:
            report.timed_out = True
            logger.warning("Verificación MCP: se agotó el tiempo (%.0fs).", self._time_budget)
        except Exception as e:  # el itinerario se entrega igual
            report.error = str(e)
            logger.warning("Verificación MCP falló: %s", e)

        logger.info(
            "Verificación MCP (%s): %d/%d lugares verificados.",
            report.source, report.verified, report.requested,
        )
        return report

    def _select_targets(self, itinerary: Itinerary) -> list[tuple[str, list[Activity]]]:
        """Agrupa actividades por lugar (sin repetir) y limita cuántos se consultan."""
        grouped: dict[str, tuple[str, list[Activity]]] = {}
        for day in itinerary.days:
            for activity in day.activities:
                place = (activity.place or "").strip()
                if not place or self._activity_type(activity) in _SKIP_TYPES:
                    continue
                key = place.lower()
                if key not in grouped:
                    grouped[key] = (place, [])
                grouped[key][1].append(activity)
        return list(grouped.values())[: self._max_lookups]

    @staticmethod
    def _activity_type(activity: Activity) -> ActivityType | str:
        try:
            return ActivityType(activity.type)
        except ValueError:
            return activity.type

    async def _locate_destination(self, session: PlacesSession, destination: str) -> Optional[GeoPoint]:
        try:
            results = await session.search(destination, limit=1)
        except Exception as e:
            logger.info("No se pudo ubicar el destino '%s': %s", destination, e)
            return None
        for r in results:
            if r.latitude is not None and r.longitude is not None:
                return GeoPoint(r.latitude, r.longitude)
        return None

    async def _verify(
        self,
        session: PlacesSession,
        place: str,
        activities: list[Activity],
        destination: str,
        center: Optional[GeoPoint],
        report: EnrichmentReport,
    ) -> None:
        query = place if destination.lower() in place.lower() else f"{place}, {destination}"
        radius = int(self._max_distance_km * 1000) if center else None
        try:
            results = await session.search(query, limit=3, near=center, radius_m=radius)
        except Exception as e:
            logger.info("No se pudo verificar '%s': %s", place, e)
            return

        best = self._pick(results, center)
        if best is None:
            return
        location = PlaceLocation(
            name=best.name,
            address=best.address,
            latitude=best.latitude,
            longitude=best.longitude,
            url=best.url,
            rating=best.rating,
            source=best.source,
            verified=True,
        )
        for activity in activities:
            activity.location = location
        report.verified += 1

    def _pick(self, results: list[PlaceResult], center: Optional[GeoPoint]) -> Optional[PlaceResult]:
        """Elige el primer resultado con coordenadas que esté cerca del destino."""
        for r in results:
            if r.latitude is None or r.longitude is None:
                continue
            if center and _haversine_km(center, r.latitude, r.longitude) > self._max_distance_km:
                continue  # coincidencia en otra ciudad: se descarta
            return r
        return None
