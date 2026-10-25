from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FACE_ACCESS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Face Recognition Access Lab"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://face_access:local-development-only@localhost:5432/face_access"
    )
    database_healthcheck_enabled: bool = True

    yunet_model_path: Path = Path("models/face_detection_yunet.onnx")
    sface_model_path: Path = Path("models/face_recognition_sface.onnx")
    detection_score_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    verification_similarity_threshold: float = Field(default=0.50, ge=-1.0, le=1.0)
    identification_similarity_threshold: float = Field(default=0.50, ge=-1.0, le=1.0)
    identification_minimum_margin: float = Field(default=0.05, ge=0.0, le=2.0)

    max_upload_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)
    max_image_pixels: int = Field(default=16_000_000, ge=1)
    minimum_enrollment_images: int = Field(default=2, ge=1)
    maximum_enrollment_images: int = Field(default=10, ge=1, le=50)
    min_face_size_px: int = Field(default=80, ge=1)
    min_blur_score: float = Field(default=60.0, gt=0.0)
    min_brightness: float = Field(default=45.0, ge=0.0, le=255.0)
    max_brightness: float = Field(default=210.0, ge=0.0, le=255.0)
    max_absolute_pose_degrees: float = Field(default=30.0, gt=0.0, le=90.0)
    temporal_confirmations: int = Field(default=3, ge=2)
    temporal_window_size: int = Field(default=5, ge=2)
    temporal_max_gap_ms: int = Field(default=1000, ge=1)
    temporal_review_after_ms: int = Field(default=5000, ge=1000, le=60_000)
    temporal_frame_interval_ms: int = Field(default=350, ge=100, le=5000)

    @model_validator(mode="after")
    def validate_brightness_range(self) -> "Settings":
        if self.min_brightness >= self.max_brightness:
            raise ValueError("min_brightness must be lower than max_brightness")
        if self.temporal_confirmations > self.temporal_window_size:
            raise ValueError("temporal_confirmations cannot exceed temporal_window_size")
        if self.minimum_enrollment_images > self.maximum_enrollment_images:
            raise ValueError("minimum_enrollment_images cannot exceed maximum_enrollment_images")
        return self
