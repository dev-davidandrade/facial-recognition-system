from face_access.adapters.database import models  # noqa: F401
from face_access.adapters.database.base import Base


def test_initial_schema_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "persons",
        "model_versions",
        "face_templates",
        "recognition_events",
        "threshold_configs",
    }
