import math

import pytest
from pydantic import ValidationError

from app.aggregate import aggregate
from app.bands import band_for
from app.cutoffs import RuleCutoffs

# Test fixture values only. They are not model cut-offs.
C = RuleCutoffs(fpr_01=1.0, fpr_05=0.0, fpr_10=-0.5)


def above(x):
    return math.nextafter(x, math.inf)


def below(x):
    return math.nextafter(x, -math.inf)


@pytest.mark.parametrize(
    "score, verdict, band",
    [
        (5.0, "scam", "high"),
        (above(C.fpr_01), "scam", "high"),
        (C.fpr_01, "scam", "medium"),  # equal to c1 is not above it
        (below(C.fpr_01), "scam", "medium"),
        (above(C.fpr_05), "scam", "medium"),
        (C.fpr_05, "not_scam", "borderline"),  # equal to c5
        (below(C.fpr_05), "not_scam", "borderline"),
        (above(C.fpr_10), "not_scam", "borderline"),
        (C.fpr_10, "not_scam", "low"),  # equal to c10
        (below(C.fpr_10), "not_scam", "low"),
        (-50.0, "not_scam", "low"),
    ],
)
def test_band_mapping_at_every_boundary(score, verdict, band):
    assert band_for(score, C) == (verdict, band)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_scores_are_rejected(bad):
    with pytest.raises(ValueError):
        band_for(bad, C)


@pytest.mark.parametrize(
    "values",
    [
        dict(fpr_01=0.0, fpr_05=1.0, fpr_10=-1.0),  # wrong order
        dict(fpr_01=1.0, fpr_05=1.0, fpr_10=0.0),  # equal cut-offs
        dict(fpr_01=1.0, fpr_05=0.0),  # missing one
    ],
)
def test_cutoffs_must_be_complete_and_strictly_ordered(values):
    with pytest.raises(ValidationError):
        RuleCutoffs(**values)


def test_placeholder_aggregate_takes_highest_piece_score():
    assert aggregate([-1.0, 0.7, 0.2], C) == 0.7


def test_aggregate_refuses_empty_scores():
    with pytest.raises(ValueError):
        aggregate([], C)
