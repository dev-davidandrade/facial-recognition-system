import uvicorn
from fastapi import FastAPI

from face_access.api.routes import router
from face_access.config.settings import Settings
from face_access.observability.logging import configure_logging


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
    application.include_router(router)
    return application


app = create_app()


def run() -> None:
    uvicorn.run("face_access.main:app", host="127.0.0.1", port=8000)
