from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sectionminer.server.routes import router


@dataclass
class ServerSettings:
    api_key: str = ""
    model: str = "gpt-4o-mini"
    extraction_backend: str = "pymupdf"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    heuristic_only: bool = False


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


def create_app(settings: ServerSettings | None = None) -> FastAPI:
    app = FastAPI(title="SectionMiner API", version="0.1")
    app.state.settings = settings or ServerSettings()
    app.state.templates_dir = TEMPLATES_DIR
    app.state.jobs = {}

    app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app

