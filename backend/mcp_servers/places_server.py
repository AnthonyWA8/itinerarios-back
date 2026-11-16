"""
Servidor MCP propio: "future-places".

Expone herramientas de lugares reales para los itinerarios, usando datos
abiertos de OpenStreetMap (Nominatim). No necesita API key.

La herramienta principal, `search_places`, replica el nombre, los parámetros
y el formato de salida de la herramienta homónima del servidor MCP oficial de
Google Maps (Grounding Lite). Así el backend puede conectarse a cualquiera de
los dos servidores sin cambiar su código: solo cambia la configuración.

Ejecución:
    python -m mcp_servers.places_server            # transporte stdio (lo usa el backend)
    python -m mcp_servers.places_server --http     # transporte HTTP en http://127.0.0.1:8765/mcp

Política de uso de Nominatim que se respeta aquí:
    - Máximo 1 petición por segundo (limitador global).
    - User-Agent que identifica la aplicación.
    - Caché de resultados para no repetir consultas.
    - Atribución "© OpenStreetMap contributors" en cada resultado.
"""

import argparse
import asyncio
import math
import os
import time
from collections import OrderedDict
from typing import Any
from urllib.parse import quote_plus

import httpx
from mcp.server.fastmcp import FastMCP

NOMINATIM_URL = os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
USER_AGENT = os.getenv(
    "OSM_USER_AGENT",
    "FuturePlannerItinerary/1.0 (+https://github.com/AnthonyWA8/itinerarios-back)",
)
MIN_SECONDS_BETWEEN_REQUESTS = float(os.getenv("OSM_MIN_INTERVAL_SECONDS", "1.05"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("OSM_TIMEOUT_SECONDS", "10"))
CACHE_SIZE = 512

ATTRIBUTION = {
    "title": "© OpenStreetMap contributors",
    "url": "https://www.openstreetmap.org/copyright",
}

# Velocidades medias (km/h) para estimar tiempos de traslado.
TRAVEL_SPEEDS_KMH = {"WALK": 4.5, "BICYCLE": 14.0, "DRIVE": 30.0, "TRANSIT": 22.0}


mcp = FastMCP(
    "future-places",
    instructions=(
        "Servidor de lugares reales para itinerarios de viaje (datos de OpenStreetMap). "
        "Usa search_places para encontrar un lugar concreto (nombre + ciudad) y obtener "
        "su dirección y coordenadas; usa estimate_travel para estimar el traslado entre "
        "dos puntos."
    ),
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8765")),
)


# ---------------------------------------------------------------------------
# Acceso a Nominatim (con límite de frecuencia y caché)
# ---------------------------------------------------------------------------

_rate_lock = asyncio.Lock()
_last_request_at = 0.0
_cache: "OrderedDict[tuple, list[dict]]" = OrderedDict()


async def _fetch_nominatim(params: dict[str, Any]) -> list[dict]:
    """Consulta Nominatim respetando 1 petición/segundo y usando caché."""
    global _last_request_at

    key = tuple(sorted(params.items()))
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]

    async with _rate_lock:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = await client.get(NOMINATIM_URL, params=params)
                response.raise_for_status()
                data = response.json()
        finally:
            _last_request_at = time.monotonic()

    results = data if isinstance(data, list) else []
    _cache[key] = results
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return results


def _viewbox_from_bias(location_bias: dict | None) -> str | None:
    """Convierte un location_bias estilo Google (círculo) en un viewbox de Nominatim."""
    if not location_bias:
        return None
    circle = location_bias.get("circle") or {}
    center = circle.get("center") or {}
    lat, lng = center.get("latitude"), center.get("longitude")
    if lat is None or lng is None:
        return None
    radius_km = float(circle.get("radius_meters") or circle.get("radiusMeters") or 20000) / 1000
    dlat = radius_km / 111.0
    dlng = radius_km / (111.0 * max(math.cos(math.radians(float(lat))), 0.01))
    return f"{lng - dlng},{lat + dlat},{lng + dlng},{lat - dlat}"


def _to_place_view(item: dict) -> dict:
    """Traduce un resultado de Nominatim al formato PlaceView de Google Grounding Lite."""
    lat = float(item["lat"])
    lng = float(item["lon"])
    osm_type = item.get("osm_type", "node")
    osm_id = item.get("osm_id", "")
    name = item.get("name") or (item.get("display_name") or "").split(",")[0].strip()
    maps_query = quote_plus(f"{lat},{lng}")
    return {
        "place": f"osm/{osm_type}/{osm_id}",
        "id": f"{osm_type}/{osm_id}",
        "displayName": {"text": name},
        "formattedAddress": item.get("display_name"),
        "types": [t for t in (item.get("category"), item.get("type")) if t],
        "location": {"latitude": lat, "longitude": lng},
        "googleMapsLinks": {
            # Enlace universal de Google Maps a las coordenadas (no requiere API key).
            "placeUrl": f"https://www.google.com/maps/search/?api=1&query={maps_query}",
            "directionsUrl": f"https://www.google.com/maps/dir/?api=1&destination={maps_query}",
        },
        "osmUrl": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        "attribution": ATTRIBUTION,
    }


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Herramientas MCP
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_places(
    text_query: str,
    page_size: int = 5,
    location_bias: dict | None = None,
    language_code: str = "es",
) -> dict[str, Any]:
    """Busca lugares reales por texto (por ejemplo "Templo Senso-ji, Tokio").

    Devuelve el mismo formato que search_places de Google Maps Grounding Lite:
    `summary` y `places[]`, donde cada lugar trae id, displayName, formattedAddress,
    location (latitude, longitude) y googleMapsLinks.placeUrl.

    Args:
        text_query: Nombre del lugar y ciudad.
        page_size: Número máximo de resultados (1 a 10).
        location_bias: Círculo opcional {"circle": {"center": {"latitude", "longitude"}, "radius_meters"}}
            que restringe la búsqueda a esa zona.
        language_code: Idioma preferido de los nombres y direcciones.
    """
    page_size = max(1, min(int(page_size), 10))
    params: dict[str, Any] = {
        "q": text_query,
        "format": "jsonv2",
        "limit": page_size,
        "addressdetails": 0,
        "accept-language": language_code,
    }
    viewbox = _viewbox_from_bias(location_bias)
    if viewbox:
        params["viewbox"] = viewbox
        params["bounded"] = 1

    items = await _fetch_nominatim(params)
    places = [_to_place_view(i) for i in items if "lat" in i and "lon" in i]
    if places:
        names = ", ".join(p["displayName"]["text"] for p in places[:3])
        summary = f"Se encontraron {len(places)} lugar(es) para '{text_query}': {names}."
    else:
        summary = f"No se encontraron lugares para '{text_query}'."
    return {"summary": summary, "places": places}


@mcp.tool()
async def estimate_travel(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    travel_mode: str = "WALK",
) -> dict[str, Any]:
    """Estima distancia y tiempo de traslado entre dos puntos.

    Usa la distancia en línea recta corregida por un factor de recorrido urbano,
    por lo que es una estimación orientativa, no una ruta exacta.

    Args:
        origin_latitude, origin_longitude: Punto de partida.
        destination_latitude, destination_longitude: Punto de llegada.
        travel_mode: WALK, BICYCLE, DRIVE o TRANSIT.
    """
    mode = travel_mode.upper()
    speed = TRAVEL_SPEEDS_KMH.get(mode, TRAVEL_SPEEDS_KMH["WALK"])
    straight_km = _haversine_km(origin_latitude, origin_longitude, destination_latitude, destination_longitude)
    route_km = straight_km * 1.3  # factor medio de recorrido real en ciudad
    minutes = round(route_km / speed * 60)
    return {
        "travel_mode": mode,
        "straight_line_km": round(straight_km, 2),
        "estimated_route_km": round(route_km, 2),
        "estimated_minutes": minutes,
        "note": "Estimación orientativa basada en distancia en línea recta.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor MCP future-places")
    parser.add_argument("--http", action="store_true", help="Usar transporte HTTP (streamable) en vez de stdio")
    args = parser.parse_args()
    mcp.run(transport="streamable-http" if args.http else "stdio")


if __name__ == "__main__":
    main()
