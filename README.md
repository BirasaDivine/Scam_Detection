# ScamGuard

A capstone research demonstration. You upload or paste an English chat, and ScamGuard returns one verdict, scam or not scam, with a confidence band.

It is not a proven detector. It has not been validated for use in Africa, and it can be wrong.

- Model: LinearSVC on TF-IDF word 1-2 grams, trained on masked text (masking v2). Small, CPU only.
- No accounts, no database, no analytics. Chats are processed in memory and never stored or logged.
- Image upload: planned for a later version.

## Layout

```
backend/    FastAPI service (Python 3.11)
  app/      routes, parsing, scoring, bands
  model/    exported model files go here (see backend/model/README.md)
  tests/    pytest
frontend/   React + Vite + TypeScript, CSS Modules
```

## Requirements

- Python 3.11 (`py -3.11 --version`)
- Node.js 22 LTS (`node --version`)

## Run the backend (PowerShell)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
$env:SCAMGUARD_ALLOWED_ORIGIN = "http://localhost:5173"
uvicorn app.main:app --port 8000 --no-access-log
```

Check it: `Invoke-RestMethod http://localhost:8000/health`

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

If any model file is missing, the backend starts in mock mode. `/health` then reports `"mock": true` and the UI shows a MOCK MODEL banner.

## Run the frontend (PowerShell)

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:5173.

## Tests

```powershell
cd backend;  .\.venv\Scripts\python -m pytest
cd frontend; npm test
```

## Model files

Put `svm_plain.joblib`, `cutoffs.json`, `masking.py` and `chunking.py` in `backend/model/`. The joblib and cutoffs files are gitignored and must never be committed. Uploaded chats must never be committed either.
