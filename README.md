# ScamGuard

A scam detection website. You upload or paste an English chat, and ScamGuard returns one verdict, scam or not scam, with a confidence band.



- Model: LinearSVC on TF-IDF word 1-2 grams, trained on masked text (masking v2). Small, CPU only.
- No accounts. Chats are processed in memory and never stored or logged. Only counts are kept: each check's verdict, chat format and, for scams, the source the user chose to report.


## Layout

```
backend/    FastAPI service (Python 3.11)
  app/      routes, parsing, scoring, bands
  model/    model files go here 
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
$env:SCAMGUARD_ALLOWED_ORIGIN = "http://localhost:5173"
uvicorn app.main:app --port 8000 --no-access-log
```


API: `POST /analyze` takes JSON `{"text": "...", "source": "whatsapp" | "plain" | "sms"}` or a multipart form with `file` (.txt, at most 1 MB) and `source`. Errors come back as `{"detail": "..."}` with 400, 413, 415, 422 or 504. Error messages never repeat what was sent.

## Counts and Insights

Each successful check is counted with its verdict (`scam` or `not_scam`), its chat format (`whatsapp`, `plain`, `sms`) and the time. The text, file name and score are never stored. `/analyze` returns a `record_id` for the counted check.

- After a scam verdict the page asks, optionally, where the message came from: WhatsApp, SMS, Telegram, Facebook, Instagram, Email, Phone call or Other. It sends `POST /checks/{record_id}/origin` with `{"origin": "..."}`. A source can be set once, and only on a scam.
- `GET /stats` returns the totals, counts per format and per scam source, and recommendations. It needs `Authorization: Bearer <SCAMGUARD_ADMIN_TOKEN>`. Without that variable set it answers 404.
- The Insights page is hidden: open `<site address>/#insights` and enter the admin token. It is not linked from the app.


How a chat is scored with the real model, as in the training notebook:

- **Single SMS:** the whole text is masked and scored as one piece.
- **WhatsApp or plain text:** the messages are joined, cut into pieces of at most 45 words (a leftover under 10 words is dropped), then each piece is masked and scored. Chats under 10 words are refused as too short.
- **Result:** the highest piece score is compared with the cut-offs in `cutoffs.json`. This rule is not yet checked on whole chats; see `backend/app/aggregate.py`.

