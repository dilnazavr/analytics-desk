FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/uploads \
    && chmod +x /app/entrypoint.sh

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]