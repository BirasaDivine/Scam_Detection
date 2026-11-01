# ScamGuard

[Deployed](https://scam-guardv2.netlify.app/)

[Technical Report](https://docs.google.com/document/d/1niwJikciS9McY1TQIOH43xWm3hk01gT_5V9z1ZnlpYI/edit?usp=sharing)

[Demo Video](https://youtu.be/ZL2sqTcvNLI)


A website that checks English chats for scams. Paste or upload a WhatsApp chat, a plain-text conversation or a single SMS, and ScamGuard returns one verdict, **scam** or **not scam**, with a confidence band.

- **Model:** LinearSVC on TF-IDF word 1-2 grams, trained on masked text. Small and CPU only.
- **Private:** no accounts. Chats are processed in memory and never stored or logged. Only counts are kept (verdict, chat format and, for scams, the source the user chose to report).
- **Insights:** a hidden admin page shows the counts and where scams come from, with recommendations.

## Technical requirements

| Area | Requirement |
|---|---|
| Operating system | Windows, macOS or Linux |
| Hardware | Any 64-bit CPU, no GPU. Runs within 512 MB RAM (Render free plan) |
| Backend | Python 3.11, FastAPI 0.143.3, Uvicorn 0.54.0, Pydantic 2.14.1 |
| Model | scikit-learn 1.6.1, spaCy 3.8.16 (`en_core_web_sm` 3.8.0), NumPy 2.1.3, pandas 2.2.3 |
| Frontend | Node.js 22, React 18.3.1, Vite 5.4.10, TypeScript 5.6.3 |
| Database | SQLite (local, default) or PostgreSQL via `DATABASE_URL` (Neon in production) |
| Testing and linting | pytest, Ruff 0.8.4, Vitest 2.1.4, Testing Library, ESLint 9.17.0 |
| Deployment | Docker on Render (backend), Netlify (frontend) |

All versions are pinned in `backend/requirements.txt` and `frontend/package.json`.

## Repository structure

```
backend/                FastAPI service
  app/                  routes, parsing, scoring, bands, counts
  model/                trained model, cut-offs, masking and chunking
  scripts/              benchmark and helper scripts
  tests/                pytest tests
  Dockerfile
frontend/               React + Vite + TypeScript, CSS Modules
  src/components/       shared UI pieces
  src/steps/            the three check steps
  src/pages/            Insights page
  src/__tests__/        Vitest tests
render.yaml             Render deployment
netlify.toml            Netlify deployment
```

## Installation

You need [Python 3.11](https://www.python.org/downloads/) and [Node.js 22](https://nodejs.org/). The commands below are for PowerShell on Windows.

**1. Get the code**

```powershell
git clone https://github.com/BirasaDivine/Scam_Detection.git
cd Scam_Detection
```

**2. Start the backend** (first terminal)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --port 8000
```

**3. Start the frontend** (second terminal, from the `Scam_Detection` folder)

```powershell
cd frontend
npm install
npm run dev
```

**4. Open http://localhost:5173** and check a chat.

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

To run the tests: `.\.venv\Scripts\python -m pytest` in `backend`, and `npm test` in `frontend`.

## API

`POST /analyze` takes JSON `{"text": "...", "source": "whatsapp" | "plain" | "sms"}` or a multipart form with `file` (.txt, at most 1 MB) and `source`. Errors come back as `{"detail": "..."}` with 400, 413, 415, 422 or 504. Error messages never repeat what was sent.

## Counts and Insights

Each successful check is counted with its verdict (`scam` or `not_scam`), its chat format (`whatsapp`, `plain`, `sms`) and the time. The text, file name and score are never stored. `/analyze` returns a `record_id` for the counted check.

- After a scam verdict the page asks, optionally, where the message came from: WhatsApp, SMS, Telegram, Facebook, Instagram, Email, Phone call or Other. It sends `POST /checks/{record_id}/origin` with `{"origin": "..."}`. A source can be set once, and only on a scam.
- `GET /stats` returns the totals, counts per format and per scam source, and recommendations. It needs `Authorization: Bearer <SCAMGUARD_ADMIN_TOKEN>`. Without that variable set it answers 404.
- The Insights page is hidden: open `<site address>/#insights` and enter the admin token. It is not linked from the app.

## How a chat is scored

With the real model, as in the training notebook:

- **Single SMS:** the whole text is masked and scored as one piece.
- **WhatsApp or plain text:** the messages are joined, cut into pieces of at most 45 words (a leftover under 10 words is dropped), then each piece is masked and scored. Chats under 10 words are refused as too short.
- **Result:** the highest piece score is compared with the cut-offs in `cutoffs.json`. This rule is not yet checked on whole chats; see `backend/app/aggregate.py`.
