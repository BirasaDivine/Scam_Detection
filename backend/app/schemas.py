from typing import Literal
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    consent_to_store: bool = False


class Reason(BaseModel):
    message_index: int
    excerpt: str
    why: str


class AnalyzeResponse(BaseModel):
    verdict: Literal["scam", "not_scam", "unsure"]
    confidence: float = Field(ge=0, le=1)
    reasons: list[Reason]
    messages_analyzed: int
    model: str
    disclaimer: str