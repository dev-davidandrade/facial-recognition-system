from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text

from face_access.config.settings import Settings


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, str]


class ReadinessProbe:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: Engine | None = None

    def check(self) -> ReadinessReport:
        checks = {
            "yunet_model": "ready" if self._settings.yunet_model_path.is_file() else "missing",
            "sface_model": "ready" if self._settings.sface_model_path.is_file() else "missing",
        }
        if self._settings.database_healthcheck_enabled:
            try:
                if self._engine is None:
                    self._engine = create_engine(
                        self._settings.database_url,
                        pool_pre_ping=True,
                        connect_args={"connect_timeout": 2},
                    )
                with self._engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                checks["database"] = "ready"
            except Exception:
                checks["database"] = "unavailable"
        else:
            checks["database"] = "disabled"

        return ReadinessReport(
            ready=all(value in {"ready", "disabled"} for value in checks.values()),
            checks=checks,
        )
