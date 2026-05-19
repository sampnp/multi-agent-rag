FROM python:3.11-slim

WORKDIR /app

# System deps needed for Playwright (browser agent) and faster-whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install Playwright Chromium browser
RUN playwright install chromium --with-deps || true

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
