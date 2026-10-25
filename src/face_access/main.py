from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from face_access.api.routes import router
from face_access.config.settings import Settings
from face_access.observability.logging import configure_logging

WEB_ROOT = Path(__file__).resolve().parent / "web"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.log_level)
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "API experimental de reconhecimento facial. Não está pronta para controle físico real."
        ),
    )
    application.mount(
        "/demo/assets",
        StaticFiles(directory=WEB_ROOT),
        name="demo-assets",
    )

    @application.get("/demo", include_in_schema=False, response_class=FileResponse)
    def demo() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    application.include_router(router)
    return application


app = create_app()


def run() -> None:
    uvicorn.run("face_access.main:app", host="127.0.0.1", port=8000)
