# ScamGuard API. Built by Render from the repo (see render.yaml) or locally:
#   docker build -t scamguard-api backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes do not reinstall them
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY model ./model

RUN useradd --create-home --uid 10001 scamguard && chown -R scamguard /app
USER scamguard

# Render sets PORT. 10000 is its default and is used when running the image by hand.
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --no-access-log"]
