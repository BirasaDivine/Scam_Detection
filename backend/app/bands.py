import math

from .cutoffs import RuleCutoffs
from .schemas import Band, Verdict


def band_for(score: float, c: RuleCutoffs) -> tuple[Verdict, Band]:
    """Map a chat score to a verdict and band. A score equal to a cut-off falls in the lower band."""
    if not math.isfinite(score):
        raise ValueError("score must be a finite number")
    if score > c.fpr_01:
        return "scam", "high"
    if score > c.fpr_05:
        return "scam", "medium"
    if score > c.fpr_10:
        return "not_scam", "borderline"
    return "not_scam", "low"
