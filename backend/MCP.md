# Integración MCP: verificación de lugares reales

El backend usa el **Model Context Protocol (MCP)** para comprobar que los lugares que propone el
LLM existen de verdad y para completar su dirección, coordenadas y enlace al mapa.

```
Usuario → RAG → LLM (gpt-oss-120b) → validador → reward model (best-of-N)
                                                        │
                                                        ▼
                                  Verificación MCP  ──►  servidor MCP de mapas
                                  (enrich_itinerary)     · Google Maps Grounding Lite (oficial, HTTP)
                                                         · future-places (propio, OpenStreetMap, stdio)
```

## Cómo funciona

1. El LLM devuelve en cada actividad un campo `place` con el nombre real del lugar (o `null` en traslados y tiempo libre).
2. `ItineraryPlacesEnricher` abre **una sesión MCP por itinerario**, ubica primero el destino y luego
   llama a la herramienta `search_places` para cada lugar único (máx. `MAPS_MAX_LOOKUPS`).
3. Se descartan las coincidencias a más de `MAPS_MAX_DISTANCE_KM` del destino (evita confundir ciudades).
4. Cada actividad verificada recibe `location` = {name, address, lat, lng, url, rating, source, verified}.
5. Es tolerante a fallos: si el servidor MCP falla o pasa `MAPS_MCP_TIMEOUT_SECONDS`, el itinerario se entrega igual.

Los dos servidores exponen la **misma herramienta con el mismo formato** (`search_places` de Google
Grounding Lite), así que se cambia de proveedor solo con configuración.

## Variables de entorno (Render → Environment)

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `MAPS_MCP_MODE` | `auto` | `auto` (Google si hay key, si no el propio) · `google` · `local` · `off` |
| `GOOGLE_MAPS_API_KEY` | vacío | API key de Google Maps Platform con la *Maps Grounding Lite API* habilitada |
| `GOOGLE_MAPS_MCP_URL` | `https://mapstools.googleapis.com/mcp` | Endpoint del MCP oficial |
| `MAPS_MCP_TIMEOUT_SECONDS` | `25` | Tiempo máximo de verificación por itinerario |
| `MAPS_MAX_LOOKUPS` | `10` | Lugares máximos consultados por itinerario |
| `MAPS_MAX_DISTANCE_KM` | `80` | Radio alrededor del destino |
| `MAPS_MCP_LOCAL_TRANSPORT` | `inprocess` | Servidor propio: `inprocess` (dentro del backend, canal en memoria) o `stdio` (subproceso) |
| `OSM_USER_AGENT` | `FuturePlannerItinerary/1.0 (+repo)` | Identificación ante Nominatim (política de uso de OSM) |

Sin ninguna variable nueva, el backend ya funciona con el servidor propio (OpenStreetMap, gratis, sin key).

## Servidor MCP propio: `future-places`

`mcp_servers/places_server.py` (FastMCP). Herramientas:

- `search_places(text_query, page_size, location_bias, language_code)`: busca lugares en OpenStreetMap (Nominatim).
- `estimate_travel(origin_*, destination_*, travel_mode)`: distancia y tiempo estimado entre dos puntos.

Si Nominatim falla o bloquea la IP del servidor, usa como respaldo Photon (otro buscador sobre OpenStreetMap, sin key).

Respeta la política de Nominatim: máximo 1 petición/segundo, User-Agent identificable, caché y atribución
"© OpenStreetMap contributors".

Ejecutarlo a mano:

```bash
python -m mcp_servers.places_server          # stdio
python -m mcp_servers.places_server --http   # Streamable HTTP en http://127.0.0.1:8765/mcp
npx @modelcontextprotocol/inspector python -m mcp_servers.places_server   # inspector visual
```

## Endpoints de demostración

- `GET /api/v1/places/mcp`: servidor MCP conectado y herramientas que expone.
- `GET /api/v1/places/search?q=Museo del Oro, Bogotá`: busca un lugar a través del MCP.

## Pruebas

```bash
pytest tests/test_mcp_places.py -q
```

Cubren el servidor propio por stdio contra un Nominatim simulado, la ruta remota por HTTP (la misma que usa
Google), el filtro de distancia, los duplicados, el límite de tiempo y el modo desactivado.
