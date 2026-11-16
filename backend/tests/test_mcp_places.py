"""
Pruebas de la integración MCP de lugares.

- Servidor MCP propio lanzado como subproceso (stdio) contra un Nominatim simulado.
- Mismo servidor expuesto por HTTP (Streamable HTTP), probado con el cliente en modo "google"
  para validar la ruta remota (cabeceras, transporte) sin depender de Google.
- Enriquecedor de itinerarios con un servicio falso (filtro de distancia, duplicados, transporte, tiempo).
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.application.use_cases.itinerary.enrich_itinerary import ItineraryPlacesEnricher
from app.domain.entities.itinerary import Activity, DayPlan, Itinerary
from app.domain.services.places_service import PlaceResult, PlacesService, PlacesSession
from app.infrastructure.mcp.mcp_places_client import MCPPlacesService, normalize_places

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- Nominatim simulado
CANNED = {
    "bogota": [{"osm_type": "relation", "osm_id": 7426387, "lat": "4.6533", "lon": "-74.0836",
                "display_name": "Bogotá, Colombia", "name": "Bogotá", "type": "city", "class": "boundary"}],
    "museo del oro": [{"osm_type": "way", "osm_id": 123, "lat": "4.6019", "lon": "-74.0721",
                       "display_name": "Museo del Oro, Carrera 6, La Candelaria, Bogotá, Colombia",
                       "name": "Museo del Oro", "type": "museum", "class": "tourism"}],
    # Coincidencia en otra ciudad (Medellín, ~240 km): debe descartarse
    "plaza botero": [{"osm_type": "node", "osm_id": 456, "lat": "6.2518", "lon": "-75.5686",
                      "display_name": "Plaza Botero, Medellín, Colombia",
                      "name": "Plaza Botero", "type": "square", "class": "place"}],
}


class _FakeNominatim(BaseHTTPRequestHandler):
    seen_user_agents: list[str] = []

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/blocked"):
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path.startswith("/photon"):
            data = json.dumps({"features": [{
                "geometry": {"type": "Point", "coordinates": [-74.0721, 4.6019]},
                "properties": {"osm_type": "W", "osm_id": 123, "name": "Museo del Oro",
                               "street": "Carrera 6", "city": "Bogotá", "country": "Colombia",
                               "osm_key": "tourism", "osm_value": "museum"},
            }]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        q = parse_qs(urlparse(self.path).query).get("q", [""])[0].lower()
        q = q.replace("á", "a")
        _FakeNominatim.seen_user_agents.append(self.headers.get("User-Agent", ""))
        body = next((v for k, v in CANNED.items() if q.startswith(k)), [])
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def fake_nominatim():
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), _FakeNominatim)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/search"
    old = {k: os.environ.get(k) for k in ("OSM_NOMINATIM_URL", "OSM_MIN_INTERVAL_SECONDS", "NO_PROXY", "no_proxy")}
    os.environ.update({"OSM_NOMINATIM_URL": url, "OSM_MIN_INTERVAL_SECONDS": "0",
                       "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"})
    yield url
    server.shutdown()
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _itinerary(*activities: Activity) -> Itinerary:
    return Itinerary(
        id=None, user_id=None, destination="Bogotá", total_days=1, total_estimated_cost=0.0,
        summary="", highlights=[],
        days=[DayPlan(day=1, title="Centro", theme="cultura", activities=list(activities), daily_budget=0.0)],
        practical_info=None, preferences=None,
    )


def _act(title: str, place, type_: str = "culture") -> Activity:
    return Activity(time="10:00", title=title, description="", type=type_, cost=0, place=place)


# ---------------------------------------------------------------- stdio (servidor propio)
def test_local_stdio_server_lists_tools_and_searches(fake_nominatim):
    async def run():
        svc = MCPPlacesService(mode="local", local_transport="stdio")
        tools = {t["name"] for t in await svc.list_tools()}
        assert {"search_places", "estimate_travel"} <= tools
        async with svc.session() as s:
            res = await s.search("Museo del Oro, Bogotá", limit=3)
        assert res and res[0].name == "Museo del Oro"
        assert res[0].source == "openstreetmap"
        assert "google.com/maps" in res[0].url
        assert abs(res[0].latitude - 4.6019) < 1e-6
    asyncio.run(run())
    assert any("FuturePlannerItinerary" in ua for ua in _FakeNominatim.seen_user_agents)


def test_enricher_end_to_end_with_local_server(fake_nominatim):
    it = _itinerary(
        _act("Visita al Museo del Oro", "Museo del Oro"),
        _act("Foto en la plaza", "Plaza Botero"),  # existe, pero en otra ciudad
        _act("Traslado al hotel", "Aeropuerto El Dorado", type_="transport"),
        _act("Tiempo libre", None),
    )
    enricher = ItineraryPlacesEnricher(MCPPlacesService(mode="local", local_transport="stdio"))
    report = asyncio.run(enricher.enrich(it))
    acts = it.days[0].activities
    assert report.requested == 2 and report.verified == 1
    assert acts[0].location and acts[0].location.verified
    assert acts[1].location is None  # descartado por distancia
    assert acts[2].location is None and acts[3].location is None


# ---------------------------------------------------------------- en memoria (modo por defecto)
@pytest.fixture
def ps_module(fake_nominatim, monkeypatch):
    import mcp_servers.places_server as ps
    monkeypatch.setattr(ps, "NOMINATIM_URL", fake_nominatim)
    monkeypatch.setattr(ps, "MIN_SECONDS_BETWEEN_REQUESTS", 0)
    ps._cache.clear()
    return ps


def test_inprocess_server_end_to_end(ps_module):
    it = _itinerary(_act("Museo", "Museo del Oro"), _act("Plaza", "Plaza Botero"))
    svc = MCPPlacesService(mode="local")  # inprocess por defecto
    assert svc.local_transport == "inprocess"
    report = asyncio.run(ItineraryPlacesEnricher(svc).enrich(it))
    assert report.error is None and report.verified == 1
    assert it.days[0].activities[0].location.name == "Museo del Oro"


def test_photon_fallback_when_nominatim_blocks(ps_module, monkeypatch):
    base = ps_module.NOMINATIM_URL.rsplit("/", 1)[0]
    monkeypatch.setattr(ps_module, "NOMINATIM_URL", f"{base}/blocked")
    monkeypatch.setattr(ps_module, "PHOTON_URL", f"{base}/photon")

    async def run():
        async with MCPPlacesService(mode="local").session() as s:
            return await s.search("Museo del Oro, Bogotá")
    [r] = asyncio.run(run())
    assert r.name == "Museo del Oro" and "Carrera 6" in r.address and abs(r.longitude + 74.0721) < 1e-6


def test_error_message_is_unwrapped():
    from app.infrastructure.mcp.mcp_places_client import describe_error
    err = ExceptionGroup("unhandled errors in a TaskGroup", [ModuleNotFoundError("No module named 'x'")])
    assert describe_error(err) == "ModuleNotFoundError: No module named 'x'"


# ---------------------------------------------------------------- HTTP (ruta remota tipo Google)
@pytest.fixture(scope="module")
def http_server(fake_nominatim):
    port = _free_port()
    env = {**os.environ, "MCP_PORT": str(port), "PYTHONPATH": str(BACKEND_ROOT)}
    proc = subprocess.Popen([sys.executable, "-m", "mcp_servers.places_server", "--http"],
                            cwd=BACKEND_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.2)
    yield f"http://127.0.0.1:{port}/mcp"
    proc.terminate()
    proc.wait(timeout=5)


def test_remote_streamable_http_path(http_server):
    async def run():
        svc = MCPPlacesService(mode="google", google_api_key="test-key", google_url=http_server)
        async with svc.session() as s:
            res = await s.search("Museo del Oro", limit=1)
        assert res[0].name == "Museo del Oro" and res[0].source == "google"
    asyncio.run(run())


# ---------------------------------------------------------------- unidades
def test_normalize_google_payload():
    payload = {"places": [{
        "place": "places/abc", "id": "abc", "displayName": {"text": "Monserrate"},
        "formattedAddress": "Bogotá, Colombia", "rating": 4.8,
        "location": {"latitude": 4.6058, "longitude": -74.0563},
        "googleMapsLinks": {"placeUrl": "https://maps.google.com/?cid=1"},
    }]}
    [r] = normalize_places(payload, "google", "x")
    assert (r.name, r.rating, r.url) == ("Monserrate", 4.8, "https://maps.google.com/?cid=1")


def test_from_settings_modes():
    class S:
        MAPS_MCP_MODE = "auto"; GOOGLE_MAPS_API_KEY = ""; GOOGLE_MAPS_MCP_URL = "u"
    assert MCPPlacesService.from_settings(S).mode == "local"
    S.GOOGLE_MAPS_API_KEY = "k"
    assert MCPPlacesService.from_settings(S).mode == "google"
    S.MAPS_MCP_MODE = "off"
    assert MCPPlacesService.from_settings(S) is None


class _SlowService(PlacesService):
    source = "fake"

    @asynccontextmanager
    async def session(self):
        class _S(PlacesSession):
            async def search(self, *a, **k):
                await asyncio.sleep(5)
                return []
        yield _S()


def test_enricher_respects_time_budget():
    it = _itinerary(_act("Museo", "Museo del Oro"))
    report = asyncio.run(ItineraryPlacesEnricher(_SlowService(), time_budget_seconds=0.3).enrich(it))
    assert report.timed_out and it.days[0].activities[0].location is None


class _CountingService(PlacesService):
    source = "fake"

    def __init__(self):
        self.queries = []

    @asynccontextmanager
    async def session(self):
        outer = self

        class _S(PlacesSession):
            async def search(self, query, **k):
                outer.queries.append(query)
                return [PlaceResult(query, None, 4.6, -74.08, None, None, "fake")]
        yield _S()


def test_enricher_dedupes_and_caps():
    svc = _CountingService()
    it = _itinerary(*[_act(f"a{i}", "Museo del Oro") for i in range(3)], _act("b", "Monserrate"))
    report = asyncio.run(ItineraryPlacesEnricher(svc, max_lookups=10).enrich(it))
    assert report.requested == 2 and report.verified == 2
    assert len(svc.queries) == 3  # destino + 2 lugares únicos
    assert all(a.location for a in it.days[0].activities)


def test_disabled_enricher_is_noop():
    it = _itinerary(_act("Museo", "Museo del Oro"))
    report = asyncio.run(ItineraryPlacesEnricher(None).enrich(it))
    assert report.verified == 0 and it.days[0].activities[0].location is None
