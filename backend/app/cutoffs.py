import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator


class RuleCutoffs(BaseModel):
    """decision_function cut-offs at 1%, 5% and 10% false-alarm rates on normal messages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fpr_01: float
    fpr_05: float
    fpr_10: float

    @model_validator(mode="after")
    def _ordered(self):
        if not (self.fpr_01 > self.fpr_05 > self.fpr_10):
            raise ValueError("cut-offs must satisfy fpr_01 > fpr_05 > fpr_10")
        return self


class CutoffsFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_version: Optional[str] = None
    trained_on: Optional[str] = None
    sms: RuleCutoffs
    dialogue: RuleCutoffs

    def for_rule(self, rule: str) -> RuleCutoffs:
        return self.sms if rule == "sms" else self.dialogue


def load_cutoffs(path: Path) -> CutoffsFile:
    return CutoffsFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
