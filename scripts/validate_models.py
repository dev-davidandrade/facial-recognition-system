import hashlib
import tomllib
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    with (MODEL_DIR / "manifest.toml").open("rb") as manifest_file:
        models: list[dict[str, Any]] = tomllib.load(manifest_file)["models"]

    for model in models:
        path = MODEL_DIR / str(model["filename"])
        if not path.is_file():
            raise FileNotFoundError(f"Modelo ausente: {path}")
        actual = sha256(path)
        if actual != model["sha256"]:
            raise RuntimeError(f"Checksum inválido para {model['id']}: {actual}")
        print(f"Checksum válido: {model['id']}")

    sface = next(model for model in models if model["id"] == "sface-2021dec")
    recognizer = cv2.FaceRecognizerSF.create(str(MODEL_DIR / sface["filename"]), "")
    synthetic_aligned_face = np.zeros((112, 112, 3), dtype=np.uint8)
    dimension = int(recognizer.feature(synthetic_aligned_face).reshape(-1).shape[0])
    expected = int(sface["expected_embedding_dimension"])
    if dimension != expected:
        raise RuntimeError(f"Dimensão SFace inesperada: {dimension}; esperada: {expected}")
    print(f"Dimensão de embedding confirmada programaticamente: {dimension}")


if __name__ == "__main__":
    main()
