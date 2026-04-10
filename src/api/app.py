"""FastAPI application factory.

Serves static files, HTML templates, and JSON API endpoints.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.graph_api import router as graph_router
from src.api.middleware import global_exception_handler
from src.api.routes_page import router as routes_router
from src.api.scenarios import router as scenarios_router
from src.api.test_cases_catalog import router as test_cases_router
from src.config import settings as default_settings
from src.core.graph_adapter import load_npz
from src.data.pems_client import PEMSClient
from src.prediction.dcrnn_provider import DCRNNProvider
from src.prediction.gru_provider import GRUProvider
from src.prediction.lstm_provider import LSTMProvider
from src.prediction.mock_provider import MockProvider

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(app_settings=None) -> FastAPI:
    if app_settings is None:
        app_settings = default_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Load shared resources once at startup and release on shutdown."""
        app.state.npz_data = load_npz(app_settings.GRAPH_NPZ_PATH)
        app.state.pems_client = PEMSClient(
            api_key=app_settings.PEMS_API_KEY,
            base_url=app_settings.PEMS_BASE_URL,
            npz_path=app_settings.GRAPH_NPZ_PATH,
        )
        app.state.providers = {
            "mock": MockProvider(),
            "gru": GRUProvider(pems_client=app.state.pems_client),
            "lstm": LSTMProvider(pems_client=app.state.pems_client),
            "dcrnn": DCRNNProvider(pems_client=app.state.pems_client),
        }
        yield

    app = FastAPI(
        title="TBRGS",
        description="Traffic-Based Route Guidance System",
        lifespan=lifespan,
    )

    app.state.settings = app_settings

    app.add_exception_handler(Exception, global_exception_handler)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    app.include_router(graph_router)
    app.include_router(routes_router)
    app.include_router(scenarios_router)
    app.include_router(test_cases_router)

    # Road geometry proxy — tries OSRM, falls back to Valhalla.
    # Server-side cache: same coords+alternatives always return the same geometry.
    _osrm_cache: dict = {}

    def _decode_polyline6(encoded: str) -> list:
        """Decode Valhalla precision-6 encoded polyline to [[lon,lat], ...]."""
        pts: list = []
        lat = lon = 0
        i = 0
        while i < len(encoded):
            for coord in range(2):
                shift = result = 0
                while True:
                    b = ord(encoded[i]) - 63
                    i += 1
                    result |= (b & 0x1F) << shift
                    shift += 5
                    if b < 0x20:
                        break
                delta = ~(result >> 1) if (result & 1) else (result >> 1)
                if coord == 0:
                    lat += delta
                else:
                    lon += delta
            pts.append([lon / 1e6, lat / 1e6])
        return pts

    async def _try_osrm(coords: str, alternatives: bool) -> dict | None:
        """Try the public OSRM server. Returns None on failure."""
        q = "overview=full&geometries=geojson"
        if alternatives:
            q += "&alternatives=true"
        url = f"https://router.project-osrm.org/route/v1/driving/{coords}?{q}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                ct = resp.headers.get("content-type", "")
                if "json" not in ct:
                    return None
                data = resp.json()
                if data.get("code") == "Ok":
                    return data
        except Exception:
            pass
        return None

    async def _try_valhalla(coords: str, alternatives: bool) -> dict | None:
        """Try Valhalla and convert response to OSRM format."""
        import json as _json
        import urllib.parse

        pairs = coords.split(";")
        locations = []
        for pair in pairs:
            parts = pair.split(",")
            if len(parts) != 2:
                return None
            locations.append({"lon": float(parts[0]), "lat": float(parts[1])})

        req = {"locations": locations, "costing": "auto"}
        if alternatives:
            req["alternates"] = 3
        url = (
            "https://valhalla1.openstreetmap.de/route?json="
            + urllib.parse.quote(_json.dumps(req))
        )
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                if "trip" not in data:
                    return None

            # Convert Valhalla response → OSRM format
            def _convert_trip(trip: dict) -> dict:
                shape = ""
                for leg in trip.get("legs", []):
                    shape = leg.get("shape", shape)
                geom_coords = _decode_polyline6(shape) if shape else []
                dist_m = trip.get("summary", {}).get("length", 0) * 1000
                return {
                    "geometry": {"type": "LineString", "coordinates": geom_coords},
                    "distance": dist_m,
                }

            routes = [_convert_trip(data["trip"])]
            for alt in data.get("alternates", []):
                if "trip" in alt:
                    routes.append(_convert_trip(alt["trip"]))

            return {"code": "Ok", "routes": routes}
        except Exception:
            return None

    @app.get("/api/osrm")
    async def osrm_proxy(coords: str, alternatives: bool = False) -> dict:
        """Proxy road-geometry requests: tries OSRM, falls back to Valhalla.

        Args:
            coords: semicolon-separated lon,lat pairs (e.g. "-121.9,37.3;-121.8,37.4")
            alternatives: if True, request multiple driving routes.
        """
        cache_key = f"{coords}|{alternatives}"
        if cache_key in _osrm_cache:
            return _osrm_cache[cache_key]

        # Try OSRM first (faster when available)
        data = await _try_osrm(coords, alternatives)
        if data is None:
            # Fall back to Valhalla (more reliable, supports alternates natively)
            data = await _try_valhalla(coords, alternatives)
        if data is None:
            return {"code": "Error", "message": "All routing servers unavailable"}

        _osrm_cache[cache_key] = data
        return data

    @app.get("/api/geocode/reverse")
    async def reverse_geocode(lat: float, lon: float) -> dict:
        """Proxy Nominatim reverse lookup (polite User-Agent; short timeout)."""
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return {"error": "coordinates out of range", "display_name": ""}
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        )
        headers = {
            "User-Agent": "TBRGS/1.0 (traffic demo; contact: local)",
            "Accept-Language": "en",
        }
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return {"display_name": "", "error": f"upstream {resp.status_code}"}
            data = resp.json()
        name = data.get("display_name") or ""
        addr = data.get("address") or {}
        short = addr.get("road") or addr.get("neighbourhood") or addr.get("suburb")
        if short and addr.get("city"):
            short = f"{short}, {addr['city']}"
        return {
            "display_name": name,
            "short_label": short or name or f"{lat:.4f}, {lon:.4f}",
        }

    # Page routes
    @app.get("/")
    async def route_finding_page(request: Request):
        return templates.TemplateResponse(request=request, name="routes.html")

    return app
