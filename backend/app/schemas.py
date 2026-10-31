from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["whatsapp", "plain", "sms"]
Verdict = Literal["scam", "not_scam"]
Band = Literal["high", "medium", "borderline", "low"]
Rule = Literal["sms", "dialogue"]
Origin = Literal["whatsapp", "sms", "telegram", "facebook", "instagram", "email", "phone_call", "other"]


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
    record_id: Optional[str] = None


class OriginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: Origin


class FormatCounts(BaseModel):
    scam: int
    not_scam: int


class StatsResponse(BaseModel):
    total: int
    scam: int
    not_scam: int
    by_input_format: dict[Source, FormatCounts]
    scam_origins: dict[Origin, int]
    scam_origin_unreported: int
    recommendations: list[str]


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_version: str
    mock: bool
