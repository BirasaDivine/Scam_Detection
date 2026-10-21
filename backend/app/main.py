from fastapi import FastAPI

# Stage 1 skeleton. /analyze is rebuilt in stage 2 against the new contract.
app = FastAPI(title="ScamGuard API")


@app.get("/health")
def health():
    return {"status": "ok", "model_version": "mock-0", "mock": True}
