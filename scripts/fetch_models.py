import argparse
import hashlib
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
MANIFEST = MODEL_DIR / "manifest.toml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(model: dict[str, Any]) -> None:
    destination = MODEL_DIR / str(model["filename"])
    temporary = destination.with_suffix(destination.suffix + ".download")
    print(f"Obtendo {model['id']} da origem registrada...")
    urllib.request.urlretrieve(str(model["source_url"]), temporary)
    actual = sha256(temporary)
    expected = str(model["sha256"])
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum inválido para {model['id']}: {actual}")
    temporary.replace(destination)
    print(f"Validado: {destination.name} ({actual})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Obtém modelos registrados e valida SHA-256.")
    parser.add_argument(
        "--accept-research-only",
        action="store_true",
        help="Confirma que os modelos serão usados somente no laboratório experimental.",
    )
    args = parser.parse_args()
    if not args.accept_research_only:
        parser.error("Leia docs/MODEL_CARD.md e informe --accept-research-only")
    with MANIFEST.open("rb") as manifest_file:
        manifest = tomllib.load(manifest_file)
    for model in manifest["models"]:
        fetch(model)


if __name__ == "__main__":
    main()
