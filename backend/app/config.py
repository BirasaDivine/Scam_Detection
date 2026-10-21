import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

MAX_FILE_BYTES = 1024 * 1024  # 1 MB, for an uploaded file or pasted text
MAX_MESSAGES = 2000
# Multipart framing around a 1 MB file is small. Anything bigger is refused before parsing.
MAX_BODY_BYTES = MAX_FILE_BYTES + 64 * 1024

DISCLAIMER = (
    "This is a research demonstration. It has not been validated for use in Africa, "
    "and it can be wrong."
)


@dataclass(frozen=True)
class Settings:
    allowed_origins: list[str]
    timeout_seconds: float
    model_dir: Path


def load_settings() -> Settings:
    origins = os.environ.get("SCAMGUARD_ALLOWED_ORIGIN", "http://localhost:5173")
    return Settings(
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
        timeout_seconds=float(os.environ.get("SCAMGUARD_TIMEOUT_SECONDS", "20")),
        model_dir=Path(os.environ.get("SCAMGUARD_MODEL_DIR", BACKEND_DIR / "model")),
    )
