from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["whatsapp", "plain", "sms"]
Verdict = Literal["scam", "not_scam"]
Band = Literal["high", "medium", "borderline", "low"]
Rule = Literal["sms", "dialogue"]


class TextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    source: Source


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Verdict
    band: Band
    pieces_scored: int = Field(ge=1)
    source_rule: Rule
    model_version: str
    disclaimer: str


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_version: str
    mock: bool
