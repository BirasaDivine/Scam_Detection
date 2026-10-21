import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import model_stubs
from .cutoffs import CutoffsFile
from .scoring import MOCK_CUTOFFS, MockScorer, Scorer

log = logging.getLogger("scamguard")

MODEL_FILES = ("svm_plain.joblib", "cutoffs.json", "masking.py", "chunking.py")


@dataclass(frozen=True)
class Engine:
    scorer: Scorer
    cutoffs: CutoffsFile
    mask: Callable[[str], str]
    chunk: Callable[[list[str]], list[str]]
    model_version: str
    mock: bool


def mock_engine(scorer: Optional[Scorer] = None) -> Engine:
    return Engine(
        scorer=scorer or MockScorer(),
        cutoffs=MOCK_CUTOFFS,
        mask=model_stubs.mask,
        chunk=model_stubs.chunk,
        model_version="mock-0",
        mock=True,
    )


def load_engine(model_dir: Path) -> Engine:
    missing = [f for f in MODEL_FILES if not (model_dir / f).is_file()]
    if missing:
        log.warning("Model files missing (%s). Starting in MOCK mode.", ", ".join(missing))
        return mock_engine()
    # Stage 4 wires SvmScorer, the exported masking and chunking, and their parity tests.
    raise RuntimeError("Model files are present but not wired yet. Remove them or finish stage 4.")


def model_version_for(cutoffs: CutoffsFile, joblib_path: Path) -> str:
    if cutoffs.model_version:
        return cutoffs.model_version
    digest = hashlib.sha256(joblib_path.read_bytes()).hexdigest()
    return f"svm_plain-{digest[:8]}"
