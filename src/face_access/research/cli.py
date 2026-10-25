import argparse
import csv
import sys
from collections.abc import Iterable, Sequence
from contextlib import nullcontext
from pathlib import Path
from typing import TextIO

from face_access.research.calibration import (
    CalibrationObservation,
    OperatingPoint,
    choose_operating_point,
    evaluate_grid,
)

DEFAULT_SIMILARITY_THRESHOLDS = (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65)
DEFAULT_QUALITY_THRESHOLDS = (0.0, 0.50, 0.60, 0.70, 0.80)


def run(arguments: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    options = parser.parse_args(arguments)
    observations = _read_observations(options.input)
    points = evaluate_grid(
        observations,
        similarity_thresholds=_parse_thresholds(options.similarity_thresholds),
        minimum_quality_scores=_parse_thresholds(options.quality_thresholds),
    )
    selected = choose_operating_point(
        points,
        maximum_false_accept_rate=options.max_far,
        minimum_coverage=options.min_coverage,
    )

    if options.output is not None:
        options.output.parent.mkdir(parents=True, exist_ok=True)
    output_context = (
        options.output.open("w", encoding="utf-8", newline="")
        if options.output is not None
        else nullcontext(sys.stdout)
    )
    with output_context as output:
        _write_points(points, output)

    if selected is None:
        print(
            "Nenhum ponto atende simultaneamente ao FAR e à cobertura solicitados.",
            file=sys.stderr,
        )
        return
    print(
        "Candidato experimental: "
        f"similaridade={selected.similarity_threshold:.3f}, "
        f"qualidade={selected.minimum_quality_score:.3f}, "
        f"FAR={selected.false_accept_rate:.4f}, "
        f"FRR={selected.false_reject_rate:.4f}, "
        f"cobertura={selected.coverage:.4f}.",
        file=sys.stderr,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Avalia uma grade de limiares em observações biométricas rotuladas.",
    )
    parser.add_argument("input", type=Path, help="CSV sem imagens ou embeddings")
    parser.add_argument("--output", type=Path, help="Arquivo CSV de saída; padrão: stdout")
    parser.add_argument(
        "--similarity-thresholds",
        default=",".join(map(str, DEFAULT_SIMILARITY_THRESHOLDS)),
        help="Lista separada por vírgulas",
    )
    parser.add_argument(
        "--quality-thresholds",
        default=",".join(map(str, DEFAULT_QUALITY_THRESHOLDS)),
        help="Lista separada por vírgulas",
    )
    parser.add_argument("--max-far", type=float, default=0.01)
    parser.add_argument("--min-coverage", type=float, default=0.80)
    return parser


def _read_observations(path: Path) -> tuple[CalibrationObservation, ...]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {"similarity", "is_genuine", "quality_score", "processing_time_ms"}
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
        return tuple(
            CalibrationObservation(
                similarity=float(row["similarity"]),
                is_genuine=_parse_boolean(row["is_genuine"]),
                quality_score=float(row["quality_score"]),
                processing_time_ms=float(row["processing_time_ms"]),
            )
            for row in reader
        )


def _parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "sim", "genuine"}:
        return True
    if normalized in {"0", "false", "no", "não", "nao", "impostor"}:
        return False
    raise ValueError(f"Invalid is_genuine value: {value}")


def _parse_thresholds(value: str) -> tuple[float, ...]:
    thresholds = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    if not thresholds:
        raise ValueError("threshold list cannot be empty")
    return thresholds


def _write_points(points: Iterable[OperatingPoint], output: TextIO) -> None:
    fields = (
        "similarity_threshold",
        "minimum_quality_score",
        "coverage",
        "genuine_accept_rate",
        "false_accept_rate",
        "false_reject_rate",
        "precision",
        "balanced_accuracy",
        "mean_processing_time_ms",
        "processed_observations",
        "deferred_observations",
        "true_accepts",
        "false_accepts",
        "true_rejects",
        "false_rejects",
    )
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for point in points:
        writer.writerow({field: getattr(point, field) for field in fields})


if __name__ == "__main__":
    run()
