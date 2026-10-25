import pytest

from face_access.research.calibration import (
    CalibrationObservation,
    choose_operating_point,
    evaluate_grid,
    evaluate_operating_point,
)


def observation(
    similarity: float,
    *,
    genuine: bool,
    quality: float,
    latency: float = 20.0,
) -> CalibrationObservation:
    return CalibrationObservation(similarity, genuine, quality, latency)


def test_operating_point_counts_quality_rejection_as_deferred_and_not_accepted() -> None:
    samples = (
        observation(0.80, genuine=True, quality=0.90),
        observation(0.40, genuine=True, quality=0.90),
        observation(0.70, genuine=False, quality=0.90),
        observation(0.20, genuine=False, quality=0.20),
    )

    point = evaluate_operating_point(
        samples,
        similarity_threshold=0.50,
        minimum_quality_score=0.50,
    )

    assert point.processed_observations == 3
    assert point.deferred_observations == 1
    assert point.coverage == 0.75
    assert point.true_accepts == 1
    assert point.false_accepts == 1
    assert point.true_rejects == 1
    assert point.false_rejects == 1
    assert point.false_accept_rate == 0.5
    assert point.false_reject_rate == 0.5


def test_grid_and_constraints_select_reproducible_candidate() -> None:
    samples = (
        observation(0.80, genuine=True, quality=0.90),
        observation(0.55, genuine=True, quality=0.80),
        observation(0.52, genuine=False, quality=0.90),
        observation(0.20, genuine=False, quality=0.80),
    )
    points = evaluate_grid(
        samples,
        similarity_thresholds=(0.50, 0.60),
        minimum_quality_scores=(0.0,),
    )

    selected = choose_operating_point(
        points,
        maximum_false_accept_rate=0.0,
        minimum_coverage=1.0,
    )

    assert selected is not None
    assert selected.similarity_threshold == 0.60
    assert selected.false_accept_rate == 0.0


def test_calibration_requires_genuine_and_impostor_observations() -> None:
    with pytest.raises(ValueError, match="impostor"):
        evaluate_operating_point(
            (observation(0.80, genuine=True, quality=0.90),),
            similarity_threshold=0.50,
            minimum_quality_score=0.50,
        )
