"""
Endpoints de consulta directa al servidor MCP de mapas.

Sirven para comprobar la conexión MCP y para demostrar el protocolo:
  - GET /api/v1/places/mcp     -> servidor conectado y herramientas que expone (descubrimiento MCP).
  - GET /api/v1/places/search  -> busca un lugar real a través de la herramienta search_places.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.services.places_service import GeoPoint
from app.infrastructure.mcp.mcp_places_client import MCPPlacesService
from app.presentation.api.dependencies import get_places_service

router = APIRouter(prefix="/api/v1/places", tags=["places-mcp"])

PlacesDep = Annotated[Optional[MCPPlacesService], Depends(get_places_service)]


def _require(service: Optional[MCPPlacesService]) -> MCPPlacesService:
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La verificación de lugares por MCP está desactivada (MAPS_MCP_MODE=off).",
        )
    return service


@router.get("/mcp")
async def mcp_status(service: PlacesDep):
    if service is None:
        return {"enabled": False, "mode": "off", "server": None, "tools": []}
    try:
        tools = await _require(service).list_tools()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo conectar con el servidor MCP ({service.server_label}): {e}",
        )
    return {"enabled": True, "mode": service.mode, "server": service.server_label, "tools": tools}


@router.get("/search")
async def search_place(
    service: PlacesDep,
    q: Annotated[str, Query(min_length=2, description="Lugar y ciudad, ej: 'Museo del Oro, Bogotá'")],
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 3,
):
    svc = _require(service)
    near = GeoPoint(lat, lng) if lat is not None and lng is not None else None
    try:
        async with svc.session() as session:
            results = await session.search(q, limit=limit, near=near, radius_m=30000 if near else None)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error en el servidor MCP: {e}")
    return {
        "mode": svc.mode,
        "results": [
            {
                "name": r.name,
                "address": r.address,
                "lat": r.latitude,
                "lng": r.longitude,
                "url": r.url,
                "rating": r.rating,
                "source": r.source,
            }
            for r in results
        ],
    }
