"""
Cliente MCP para lugares reales.

Implementa el puerto PlacesService hablando el protocolo MCP (Model Context
Protocol) con uno de estos dos servidores, que exponen la misma herramienta
`search_places` con el mismo formato:

  - google: servidor MCP oficial de Google Maps (Grounding Lite), remoto, por
    HTTP, autenticado con la cabecera X-Goog-Api-Key.
  - local:  servidor MCP propio del proyecto (mcp_servers/places_server.py),
    basado en OpenStreetMap. Por defecto corre dentro del mismo proceso del
    backend y se comunica con el cliente por un canal en memoria (mismo
    protocolo MCP, JSON-RPC). Con MAPS_MCP_LOCAL_TRANSPORT=stdio se lanza como
    subproceso y se comunica por stdio.
"""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.memory import create_connected_server_and_client_session

from app.domain.services.places_service import (
    GeoPoint,
    PlaceResult,
    PlacesError,
    PlacesService,
    PlacesSession,
)

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
LOCAL_SERVER_MODULE = "mcp_servers.places_server"
SEARCH_TOOL = "search_places"

# Variables que se pasan al subproceso del servidor propio.
_FORWARDED_ENV = (
    "OSM_NOMINATIM_URL", "OSM_USER_AGENT", "OSM_MIN_INTERVAL_SECONDS", "OSM_TIMEOUT_SECONDS",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
)


def describe_error(exc: BaseException) -> str:
    """Devuelve la causa real de un error, desempaquetando los ExceptionGroup de anyio."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return f"{type(exc).__name__}: {exc}"


def _extract_payload(result: Any) -> dict:
    """Obtiene el JSON de la respuesta de una herramienta MCP (estructurado o como texto)."""
    if getattr(result, "structuredContent", None):
        return result.structuredContent
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def _text_of(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("text")
    return value.strip() if isinstance(value, str) and value.strip() else None


def normalize_places(payload: dict, source: str, fallback_name: str) -> list[PlaceResult]:
    """Convierte la salida de search_places (formato Google Grounding Lite) en PlaceResult."""
    results: list[PlaceResult] = []
    for p in payload.get("places") or []:
        if not isinstance(p, dict):
            continue
        location = p.get("location") or {}
        links = p.get("googleMapsLinks") or {}
        rating = p.get("rating")
        results.append(
            PlaceResult(
                name=_text_of(p.get("displayName")) or _text_of(p.get("name")) or fallback_name,
                address=_text_of(p.get("formattedAddress")) or _text_of(p.get("shortFormattedAddress")),
                latitude=location.get("latitude"),
                longitude=location.get("longitude"),
                url=links.get("placeUrl") or p.get("googleMapsUri") or p.get("osmUrl"),
                rating=float(rating) if isinstance(rating, (int, float)) else None,
                source=source,
            )
        )
    return results


class _MCPPlacesSession(PlacesSession):
    def __init__(self, session: ClientSession, source: str):
        self._session = session
        self._source = source

    async def search(
        self,
        query: str,
        *,
        limit: int = 3,
        near: Optional[GeoPoint] = None,
        radius_m: Optional[int] = None,
    ) -> list[PlaceResult]:
        arguments: dict[str, Any] = {
            "text_query": query,
            "page_size": limit,
            "language_code": "es",
        }
        if near is not None:
            circle: dict[str, Any] = {
                "center": {"latitude": near.latitude, "longitude": near.longitude}
            }
            if radius_m:
                circle["radius_meters"] = radius_m
            arguments["location_bias"] = {"circle": circle}

        result = await self._session.call_tool(SEARCH_TOOL, arguments)
        if result.isError:
            detail = " ".join(getattr(c, "text", "") for c in result.content or [])
            raise PlacesError(f"La herramienta {SEARCH_TOOL} devolvió un error: {detail[:300]}")
        return normalize_places(_extract_payload(result), self._source, query)


class MCPPlacesService(PlacesService):
    """Proveedor de lugares que se conecta a un servidor MCP (Google o propio)."""

    def __init__(
        self,
        mode: str,
        google_api_key: str = "",
        google_url: str = "https://mapstools.googleapis.com/mcp",
        local_transport: str = "inprocess",
    ):
        self.mode = mode  # "google" | "local"
        self.local_transport = "stdio" if local_transport == "stdio" else "inprocess"
        self.source = "google" if mode == "google" else "openstreetmap"
        self._google_api_key = google_api_key
        self._google_url = google_url

    @classmethod
    def from_settings(cls, settings) -> Optional["MCPPlacesService"]:
        """Crea el servicio según MAPS_MCP_MODE. Devuelve None si está desactivado."""
        mode = (settings.MAPS_MCP_MODE or "auto").strip().lower()
        key = (settings.GOOGLE_MAPS_API_KEY or "").strip()
        if mode == "off":
            return None
        if mode == "auto":
            mode = "google" if key else "local"
        if mode == "google" and not key:
            logger.warning("MAPS_MCP_MODE=google sin GOOGLE_MAPS_API_KEY: se usa el servidor MCP propio.")
            mode = "local"
        if mode not in ("google", "local"):
            logger.warning("MAPS_MCP_MODE desconocido (%s): se usa el servidor MCP propio.", mode)
            mode = "local"
        return cls(
            mode=mode,
            google_api_key=key,
            google_url=settings.GOOGLE_MAPS_MCP_URL,
            local_transport=(getattr(settings, "MAPS_MCP_LOCAL_TRANSPORT", "inprocess") or "inprocess").lower(),
        )

    @property
    def server_label(self) -> str:
        if self.mode == "google":
            return f"Google Maps Grounding Lite ({self._google_url})"
        return f"Servidor MCP propio future-places (OpenStreetMap, {self.local_transport})"

    @asynccontextmanager
    async def _client_session(self) -> AsyncIterator[ClientSession]:
        if self.mode == "google":
            headers = {
                "X-Goog-Api-Key": self._google_api_key,
                "Accept": "application/json, text/event-stream",
            }
            async with streamablehttp_client(self._google_url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        elif self.local_transport == "inprocess":
            from mcp_servers.places_server import mcp as places_mcp

            async with create_connected_server_and_client_session(places_mcp._mcp_server) as session:
                yield session
        else:
            env = get_default_environment()
            env.update({k: v for k, v in os.environ.items() if k in _FORWARDED_ENV})
            env["PYTHONPATH"] = str(BACKEND_ROOT)
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", LOCAL_SERVER_MODULE],
                env=env,
                cwd=str(BACKEND_ROOT),
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[PlacesSession]:
        async with self._client_session() as session:
            yield _MCPPlacesSession(session, self.source)

    async def list_tools(self) -> list[dict]:
        """Descubre las herramientas que expone el servidor MCP conectado."""
        async with self._client_session() as session:
            tools = await session.list_tools()
            return [{"name": t.name, "description": (t.description or "").strip()} for t in tools.tools]
