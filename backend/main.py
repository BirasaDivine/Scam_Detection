from fastapi import FastAPI
from schemas import AnalyzeRequest, AnalyzeResponse, Reason
from chat_parser import parse_chat
from masking import mask

app = FastAPI(title="ScamGuard API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    # STUB: not a real model. It only lets us build the frontend.
    messages = parse_chat(req.text)
    texts = [mask(m.text) for m in messages]   # only masked text is used from here on
    hit = next(
        ((i, t) for i, t in enumerate(texts)
         if "fee" in t.lower() or "urgent" in t.lower()),
        None,
    )
    if hit:
        i, text = hit
        return AnalyzeResponse(
            verdict="scam",
            confidence=0.90,
            reasons=[Reason(message_index=i, excerpt=text[:120], why="Stub rule: mentions a fee or urgency")],
            messages_analyzed=len(messages),
            model="stub-v0",
            disclaimer="This is a warning, not proof.",
        )
    return AnalyzeResponse(
        verdict="not_scam",
        confidence=0.60,
        reasons=[],
        messages_analyzed=len(messages),
        model="stub-v0",
        disclaimer="This is a warning, not proof.",
    )