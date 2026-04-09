"""FastAPI application factory.

Serves static files, HTML templates, and JSON API endpoints.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.graph_api import router as graph_router
from src.api.routes_page import router as routes_router
from src.api.models_page import router as models_router

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="TBRGS",
        description="Traffic-Based Route Guidance System",
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    app.include_router(graph_router)
    app.include_router(routes_router)
    app.include_router(models_router)

    # OSRM proxy -- avoids browser CORS issues with the public OSRM API
    import httpx

    @app.get("/api/osrm")
    async def osrm_proxy(coords: str) -> dict:
        """Proxy OSRM route requests to get road-following geometries.

        Args:
            coords: semicolon-separated lon,lat pairs (e.g. "-121.9,37.3;-121.8,37.4")
        """
        url = f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            return resp.json()

    # Testing API endpoint
    @app.get("/api/testing/run")
    async def run_tests() -> dict:
        """Run pytest and return results."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr

        # Parse test results from verbose output
        test_results = []
        for line in output.splitlines():
            if "PASSED" in line or "FAILED" in line:
                parts = line.strip().split(" ")
                name = parts[0].split("::")[-1] if "::" in parts[0] else parts[0]
                status = "passed" if "PASSED" in line else "failed"
                test_results.append({"name": name, "status": status, "duration": ""})

        return {"output": output, "results": test_results, "returncode": result.returncode}

    # Page routes
    from fastapi import Request

    @app.get("/")
    async def route_finding_page(request: Request):
        return templates.TemplateResponse(request=request, name="routes.html")

    @app.get("/models")
    async def model_comparison_page(request: Request):
        return templates.TemplateResponse(request=request, name="models.html")

    @app.get("/testing")
    async def testing_page(request: Request):
        return templates.TemplateResponse(request=request, name="testing.html")

    return app
