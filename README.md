# ScamGuard

A capstone research demonstration. You upload or paste an English chat, and ScamGuard returns one verdict, scam or not scam, with a confidence band.

It is not a proven detector. It has not been validated for use in Africa, and it can be wrong.

- Model: LinearSVC on TF-IDF word 1-2 grams, trained on masked text (masking v2). Small, CPU only.
- No accounts. Chats are processed in memory and never stored or logged. Only counts are kept: each check's verdict, chat format and, for scams, the source the user chose to report.
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
$env:SCAMGUARD_ALLOWED_ORIGIN = "http://localhost:5173"
uvicorn app.main:app --port 8000 --no-access-log
```

Settings are read from environment variables (see `backend/.env.example` for the list): `SCAMGUARD_ALLOWED_ORIGIN`, `SCAMGUARD_TIMEOUT_SECONDS` (default 20), `SCAMGUARD_MODEL_DIR` (default `backend/model`), `DATABASE_URL` (default: SQLite at `backend/data/scamguard.db`) and `SCAMGUARD_ADMIN_TOKEN`.

API: `POST /analyze` takes JSON `{"text": "...", "source": "whatsapp" | "plain" | "sms"}` or a multipart form with `file` (.txt, at most 1 MB) and `source`. Errors come back as `{"detail": "..."}` with 400, 413, 415, 422 or 504. Error messages never repeat what was sent.

## Counts and Insights

Each successful check is counted with its verdict (`scam` or `not_scam`), its chat format (`whatsapp`, `plain`, `sms`) and the time. The text, file name and score are never stored. `/analyze` returns a `record_id` for the counted check.

- After a scam verdict the page asks, optionally, where the message came from: WhatsApp, SMS, Telegram, Facebook, Instagram, Email, Phone call or Other. It sends `POST /checks/{record_id}/origin` with `{"origin": "..."}`. A source can be set once, and only on a scam.
- `GET /stats` returns the totals, counts per format and per scam source, and recommendations. It needs `Authorization: Bearer <SCAMGUARD_ADMIN_TOKEN>`. Without that variable set it answers 404.
- The Insights page is hidden: open `<site address>/#insights` and enter the admin token. It is not linked from the app.
- Recommendations start after 5 checks. The main scam channel is named once at least 5 scams have a reported source and one source has 40% or more of them (`backend/app/insights.py`).

Without `DATABASE_URL`, counts go to a SQLite file. Set `DATABASE_URL` to a Postgres address to keep them on a server.

Check it: `Invoke-RestMethod http://localhost:8000/health`

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

If any model file is missing, the backend starts in mock mode. `/health` then reports `"mock": true` and the UI shows a MOCK MODEL banner. If all four files are present but cannot be loaded, the backend refuses to start instead of falling back to mock.

How a chat is scored with the real model, as in the training notebook:

- **Single SMS:** the whole text is masked and scored as one piece.
- **WhatsApp or plain text:** the messages are joined, cut into pieces of at most 45 words (a leftover under 10 words is dropped), then each piece is masked and scored. Chats under 10 words are refused as too short.
- **Result:** the highest piece score is compared with the cut-offs in `cutoffs.json` (placeholder rule, see `backend/app/aggregate.py`).

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

Put `svm_plain.joblib`, `cutoffs.json`, `masking.py` and `chunking.py` in `backend/model/`. They are committed, because Render builds the backend image from the repo. `golden_cases.json` and the notebook are gitignored. Uploaded chats must never be committed.

## Deploy

The backend runs on Render and the frontend on Netlify, both built from this GitHub repo. Each needs the other's address, so choose the Netlify site name first.

### 1. Choose the Netlify address

Pick a site name, for example `scamguard-demo`. The address is then `https://scamguard-demo.netlify.app`. You enter the same name in step 3.

### 2. Backend on Render

1. Push the repo to GitHub.
2. In Render choose **New > Blueprint** and pick the repo. Render reads `render.yaml` and builds `backend/Dockerfile`.
3. Render asks for three values. Set `SCAMGUARD_ALLOWED_ORIGIN` to the Netlify address from step 1, with no trailing slash. Set `DATABASE_URL` to a free Postgres address from [Neon](https://neon.tech) or [Supabase](https://supabase.com) (create a project and copy its connection string). Set `SCAMGUARD_ADMIN_TOKEN` to a long random secret for the Insights page.
4. Apply. The first build takes several minutes.
5. When the service is live, open `https://<your-service>.onrender.com/health`. It must show `"mock": false`. Note the service address.

### 3. Frontend on Netlify

1. Choose **Add new site > Import an existing project** and pick the repo. Netlify reads `netlify.toml`, so there is nothing to type for the build.
2. Set the site name to the one from step 1.
3. Under **Site configuration > Environment variables** add `VITE_API_URL` with the Render address, for example `https://scamguard-api.onrender.com`, with no trailing slash.
4. Deploy. If you deploy before setting `VITE_API_URL`, the build stops and says so. Set it and deploy again.

### Environment variables

| Where | Name | Value |
| --- | --- | --- |
| Render | `SCAMGUARD_ALLOWED_ORIGIN` | Netlify address. Several can be separated with commas, for example to add a custom domain. |
| Render | `SCAMGUARD_REQUIRE_MODEL` | Already `1` in `render.yaml`. The deploy stops if a model file is missing, instead of serving the mock. |
| Render | `SCAMGUARD_TIMEOUT_SECONDS` | Already `20` in `render.yaml`. |
| Render | `DATABASE_URL` | Postgres address for the counts. Without it, counts go to SQLite on Render's disk and are lost on every restart or redeploy. |
| Render | `SCAMGUARD_ADMIN_TOKEN` | Secret for `/stats` and the Insights page. Without it, both are off. |
| Netlify | `VITE_API_URL` | Render address. It is read at build time, so changing it needs a new deploy. |

### Things to know

- **Free plan sleep:** a free Render service sleeps after 15 minutes without requests. The first check after a sleep can take up to a minute. The page wakes the service as soon as it opens, so this is usually hidden while the person adds their chat.
- **Memory:** the backend uses about 200 MB, which fits the 512 MB free plan.
- **Changing a variable** on Render or Netlify restarts or rebuilds the service by itself.
- **Updating the model:** replace the files in `backend/model/`, run the backend tests, commit and push. Render redeploys on every push.

### If something does not work

| Symptom | Cause |
| --- | --- |
| The page says it could not reach the checker | `SCAMGUARD_ALLOWED_ORIGIN` does not match the Netlify address exactly. Check `https`, spelling and the trailing slash. Or the service is still waking up, so try again. |
| Netlify build fails with "VITE_API_URL is not set" | Add the variable and deploy again. |
| Render deploy fails with "SCAMGUARD_REQUIRE_MODEL is set but these model files are missing" | A file in `backend/model/` was not committed. |
| Insights says the token is not right, or that insights are off | `SCAMGUARD_ADMIN_TOKEN` on Render is missing or different from what you typed. |
| Insights counts reset to zero | `DATABASE_URL` is not set on Render, so counts were kept on its temporary disk. |
| The page shows the MOCK MODEL banner | The backend is running without model files. This cannot happen on Render while `SCAMGUARD_REQUIRE_MODEL` is `1`. |

To try the image on your computer first:

```powershell
docker build -t scamguard-api backend
docker run --rm -p 8000:10000 -e SCAMGUARD_ALLOWED_ORIGIN=http://localhost:5173 -e SCAMGUARD_REQUIRE_MODEL=1 scamguard-api
```
