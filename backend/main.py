from fastapi import FastAPI

app = FastAPI(title="ScamGuard API")

@app.get("/health")
def health():
    return {"status": "ok"}