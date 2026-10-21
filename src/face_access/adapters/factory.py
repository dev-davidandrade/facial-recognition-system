from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from face_access.adapters.detection.yunet import YuNetFaceDetector
from face_access.adapters.embeddings.sface import SFaceModel
from face_access.adapters.image_decoder import OpenCVImageDecoder
from face_access.adapters.quality import OpenCVFaceQualityEvaluator
from face_access.application.verification import (
    CompareFacesUseCase,
    EncodedImageVerificationService,
    VerificationHandler,
    VerificationThresholds,
)
from face_access.config.settings import Settings
from face_access.domain.enums import LicenseStatus
from face_access.domain.models import ModelDescriptor
from face_access.domain.ports import (
    FaceAligner,
    FaceDetector,
    FaceEmbedder,
    FaceQualityEvaluator,
    ImageDecoder,
)
from face_access.domain.services import CosineFaceMatcher


@dataclass(frozen=True, slots=True)
class VisionComponents:
    decoder: ImageDecoder
    detector: FaceDetector
    aligner: FaceAligner
    embedder: FaceEmbedder
    quality_evaluator: FaceQualityEvaluator
    model_descriptor: ModelDescriptor


def build_vision_components(settings: Settings) -> VisionComponents:
    detector = YuNetFaceDetector(
        settings.yunet_model_path,
        score_threshold=settings.detection_score_threshold,
    )
    sface = SFaceModel(settings.sface_model_path)
    quality = OpenCVFaceQualityEvaluator(
        min_face_size_px=settings.min_face_size_px,
        min_blur_score=settings.min_blur_score,
        min_brightness=settings.min_brightness,
        max_brightness=settings.max_brightness,
    )
    decoder = OpenCVImageDecoder(
        max_bytes=settings.max_upload_bytes,
        max_pixels=settings.max_image_pixels,
    )
    descriptor = ModelDescriptor(
        detector_name="yunet",
        detector_version=detector.version,
        embedder_name="sface",
        embedder_version=sface.model_version,
        embedding_dimension=128,
        model_checksum=_combined_checksum((settings.yunet_model_path, settings.sface_model_path)),
        license_status=LicenseStatus.RESEARCH_ONLY,
    )
    return VisionComponents(decoder, detector, sface, sface, quality, descriptor)


def build_verification_handler(
    settings: Settings,
    components: VisionComponents | None = None,
) -> VerificationHandler:
    vision = components or build_vision_components(settings)
    comparison = CompareFacesUseCase(
        detector=vision.detector,
        aligner=vision.aligner,
        embedder=vision.embedder,
        matcher=CosineFaceMatcher(),
        quality_evaluator=vision.quality_evaluator,
        thresholds=VerificationThresholds(settings.verification_similarity_threshold),
    )
    decoder = vision.decoder
    return EncodedImageVerificationService(decoder, comparison)


def _combined_checksum(paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in paths:
        with path.open("rb") as model_file:
            for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()
