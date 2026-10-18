from fastapi import FastAPI
from schemas import AnalyzeRequest, AnalyzeResponse, Reason

app = FastAPI(title="ScamGuard API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    # STUB: not a real model. It only lets us build the frontend.
    lines = [l for l in req.text.splitlines() if l.strip()]
    hit = next(
        ((i, l) for i, l in enumerate(lines) if "fee" in l.lower() or "urgent" in l.lower()),
        None,
    )
    if hit:
        i, line = hit
        return AnalyzeResponse(
            verdict="scam",
            confidence=0.90,
            reasons=[Reason(message_index=i, excerpt=line[:120], why="Stub rule: mentions a fee or urgency")],
            messages_analyzed=len(lines),
            model="stub-v0",
            disclaimer="This is a warning, not proof.",
        )
    return AnalyzeResponse(
        verdict="not_scam",
        confidence=0.60,
        reasons=[],
        messages_analyzed=len(lines),
        model="stub-v0",
        disclaimer="This is a warning, not proof.",
    )