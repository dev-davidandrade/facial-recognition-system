from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from statistics import fmean


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    """Uma comparação rotulada, sem imagem, embedding ou identidade pessoal."""

    similarity: float
    is_genuine: bool
    quality_score: float
    processing_time_ms: float

    def __post_init__(self) -> None:
        if not isfinite(self.similarity) or not -1.0 <= self.similarity <= 1.0:
            raise ValueError("similarity must be finite and between -1 and 1")
        if not isfinite(self.quality_score) or not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be finite and between 0 and 1")
        if not isfinite(self.processing_time_ms) or self.processing_time_ms < 0.0:
            raise ValueError("processing_time_ms must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class OperatingPoint:
    similarity_threshold: float
    minimum_quality_score: float
    total_observations: int
    processed_observations: int
    deferred_observations: int
    genuine_observations: int
    impostor_observations: int
    true_accepts: int
    false_accepts: int
    true_rejects: int
    false_rejects: int
    coverage: float
    genuine_accept_rate: float
    false_accept_rate: float
    false_reject_rate: float
    precision: float | None
    balanced_accuracy: float
    mean_processing_time_ms: float


def evaluate_operating_point(
    observations: Iterable[CalibrationObservation],
    *,
    similarity_threshold: float,
    minimum_quality_score: float,
) -> OperatingPoint:
    samples = tuple(observations)
    _validate_inputs(samples, similarity_threshold, minimum_quality_score)

    genuine_count = sum(sample.is_genuine for sample in samples)
    impostor_count = len(samples) - genuine_count
    processed = 0
    deferred = 0
    true_accepts = 0
    false_accepts = 0
    true_rejects = 0
    false_rejects = 0

    for sample in samples:
        meets_quality = sample.quality_score >= minimum_quality_score
        if meets_quality:
            processed += 1
        else:
            deferred += 1
        predicted_match = meets_quality and sample.similarity >= similarity_threshold

        if sample.is_genuine:
            if predicted_match:
                true_accepts += 1
            else:
                false_rejects += 1
        elif predicted_match:
            false_accepts += 1
        else:
            true_rejects += 1

    predicted_accepts = true_accepts + false_accepts
    genuine_accept_rate = true_accepts / genuine_count
    false_accept_rate = false_accepts / impostor_count
    false_reject_rate = false_rejects / genuine_count
    true_reject_rate = true_rejects / impostor_count

    return OperatingPoint(
        similarity_threshold=similarity_threshold,
        minimum_quality_score=minimum_quality_score,
        total_observations=len(samples),
        processed_observations=processed,
        deferred_observations=deferred,
        genuine_observations=genuine_count,
        impostor_observations=impostor_count,
        true_accepts=true_accepts,
        false_accepts=false_accepts,
        true_rejects=true_rejects,
        false_rejects=false_rejects,
        coverage=processed / len(samples),
        genuine_accept_rate=genuine_accept_rate,
        false_accept_rate=false_accept_rate,
        false_reject_rate=false_reject_rate,
        precision=true_accepts / predicted_accepts if predicted_accepts else None,
        balanced_accuracy=(genuine_accept_rate + true_reject_rate) / 2,
        mean_processing_time_ms=fmean(sample.processing_time_ms for sample in samples),
    )


def evaluate_grid(
    observations: Iterable[CalibrationObservation],
    *,
    similarity_thresholds: Sequence[float],
    minimum_quality_scores: Sequence[float],
) -> tuple[OperatingPoint, ...]:
    samples = tuple(observations)
    if not similarity_thresholds:
        raise ValueError("at least one similarity threshold is required")
    if not minimum_quality_scores:
        raise ValueError("at least one quality threshold is required")
    return tuple(
        evaluate_operating_point(
            samples,
            similarity_threshold=similarity_threshold,
            minimum_quality_score=minimum_quality,
        )
        for minimum_quality in minimum_quality_scores
        for similarity_threshold in similarity_thresholds
    )


def choose_operating_point(
    points: Iterable[OperatingPoint],
    *,
    maximum_false_accept_rate: float,
    minimum_coverage: float,
) -> OperatingPoint | None:
    if not 0.0 <= maximum_false_accept_rate <= 1.0:
        raise ValueError("maximum_false_accept_rate must be between 0 and 1")
    if not 0.0 <= minimum_coverage <= 1.0:
        raise ValueError("minimum_coverage must be between 0 and 1")
    eligible = (
        point
        for point in points
        if point.false_accept_rate <= maximum_false_accept_rate
        and point.coverage >= minimum_coverage
    )
    return max(
        eligible,
        key=lambda point: (
            point.genuine_accept_rate,
            point.balanced_accuracy,
            point.coverage,
            point.similarity_threshold,
            point.minimum_quality_score,
        ),
        default=None,
    )


def _validate_inputs(
    samples: tuple[CalibrationObservation, ...],
    similarity_threshold: float,
    minimum_quality_score: float,
) -> None:
    if not samples:
        raise ValueError("at least one observation is required")
    if not any(sample.is_genuine for sample in samples):
        raise ValueError("calibration requires at least one genuine observation")
    if not any(not sample.is_genuine for sample in samples):
        raise ValueError("calibration requires at least one impostor observation")
    if not isfinite(similarity_threshold) or not -1.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be finite and between -1 and 1")
    if not isfinite(minimum_quality_score) or not 0.0 <= minimum_quality_score <= 1.0:
        raise ValueError("minimum_quality_score must be finite and between 0 and 1")
