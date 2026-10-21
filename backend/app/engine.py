import hashlib
import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional

from . import model_stubs
from .cutoffs import CutoffsFile, load_cutoffs
from .scoring import MOCK_CUTOFFS, MockScorer, Scorer, SvmScorer

log = logging.getLogger("scamguard")

MODEL_FILES = ("svm_plain.joblib", "cutoffs.json", "masking.py", "chunking.py")

# Turns the texts of a chat's messages into the masked pieces the model scores.
# Arguments: message texts (no sender names) and the rule, "sms" or "dialogue".
Prepare = Callable[[list[str], str], list[str]]


@dataclass(frozen=True)
class Engine:
    scorer: Scorer
    cutoffs: CutoffsFile
    prepare: Prepare
    model_version: str
    mock: bool


def mock_engine(scorer: Optional[Scorer] = None) -> Engine:
    return Engine(
        scorer=scorer or MockScorer(),
        cutoffs=MOCK_CUTOFFS,
        prepare=model_stubs.prepare,
        model_version="mock-0",
        mock=True,
    )


def load_module(path: Path) -> ModuleType:
    """Import a model file by path. backend/model is not a package and the files are not edited here."""
    spec = importlib.util.spec_from_file_location(f"scamguard_model_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_prepare(masking: ModuleType, chunking: ModuleType) -> Prepare:
    """Same steps as the notebook.

    Single SMS: the whole text is masked and scored as one piece. Real SMS were never
    chunked in training, so there is no minimum length.
    Chats: the messages are joined, cut into pieces with make_pieces (at most 45 words,
    leftovers under 10 words dropped), then each piece is masked. Training chunked the raw
    dialogue first and masked each piece afterwards, so the order matters.
    """
    import pandas as pd

    def prepare(texts: list[str], rule: str) -> list[str]:
        if rule == "sms":
            whole = "\n".join(texts).strip()
            return masking.mask_texts([whole]) if whole else []
        frame = pd.DataFrame({"dialogue": [" ".join(texts)], "type": ["chat"], "label": [0]})
        made = chunking.make_pieces(frame)
        pieces = made["dialogue"].tolist() if len(made) else []  # empty frame has no columns
        return masking.mask_texts(pieces) if pieces else []

    return prepare


def load_engine(model_dir: Path, require_model: bool = False) -> Engine:
    missing = [f for f in MODEL_FILES if not (model_dir / f).is_file()]
    if missing and require_model:
        raise RuntimeError(
            f"SCAMGUARD_REQUIRE_MODEL is set but these model files are missing: {', '.join(missing)}."
        )
    if missing:
        log.warning("Model files missing (%s). Starting in MOCK mode.", ", ".join(missing))
        return mock_engine()
    try:
        cutoffs = load_cutoffs(model_dir / "cutoffs.json")
        scorer = SvmScorer(model_dir / "svm_plain.joblib")
        masking = load_module(model_dir / "masking.py")
        chunking = load_module(model_dir / "chunking.py")
        masking.mask_texts(["warm up"])  # loads spaCy now, not on the first request
        version = model_version_for(cutoffs, model_dir / "svm_plain.joblib")
    except Exception as exc:
        # Refuse to start rather than quietly fall back to mock while real files are present.
        raise RuntimeError(
            f"The model files in {model_dir} could not be loaded ({type(exc).__name__}). "
            "Check them against versions.txt."
        ) from None
    log.info("Model loaded: %s", version)
    return Engine(scorer, cutoffs, make_prepare(masking, chunking), version, mock=False)


def model_version_for(cutoffs: CutoffsFile, joblib_path: Path) -> str:
    if cutoffs.model_version:
        return cutoffs.model_version
    digest = hashlib.sha256(joblib_path.read_bytes()).hexdigest()
    return f"svm_plain-{digest[:8]}"
