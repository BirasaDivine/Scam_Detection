import re
from abc import ABC, abstractmethod
from pathlib import Path

from .cutoffs import CutoffsFile, RuleCutoffs


class Scorer(ABC):
    @abstractmethod
    def score_pieces(self, pieces: list[str]) -> list[float]:
        """One decision score per piece. Higher means more scam-like."""


class MockScorer(Scorer):
    """MOCK. Not a model and not trained on anything.

    The score is the number of distinct trigger words in a piece, so every band can be
    shown in the UI. It says nothing about how the real model behaves.
    """

    TRIGGERS = re.compile(
        r"\b(fee|urgent|verify|pin|prize|winner|password|otp|send money|blocked)\b",
        re.IGNORECASE,
    )

    def score_pieces(self, pieces: list[str]) -> list[float]:
        return [float(len({m.lower() for m in self.TRIGGERS.findall(p)})) for p in pieces]


# MOCK cut-offs that match MockScorer's word counts. Not model values.
# 3+ trigger words -> high, 2 -> medium, 1 -> borderline, 0 -> low.
_MOCK_RULE = RuleCutoffs(fpr_01=2.5, fpr_05=1.5, fpr_10=0.5)
MOCK_CUTOFFS = CutoffsFile(model_version="mock-0", trained_on="mock", sms=_MOCK_RULE, dialogue=_MOCK_RULE)


class SvmScorer(Scorer):
    """Loads backend/model/svm_plain.joblib (TF-IDF + LinearSVC) and uses decision_function."""

    def __init__(self, path: Path):
        import joblib

        self._model = joblib.load(path)

    def score_pieces(self, pieces: list[str]) -> list[float]:
        return [float(s) for s in self._model.decision_function(pieces)]
