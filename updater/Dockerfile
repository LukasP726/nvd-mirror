FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --system --uid 10001 updater \
    && mkdir -p /data \
    && chown updater:updater /data

COPY updater.py .

USER 10001

CMD ["python", "-u", "updater.py"]