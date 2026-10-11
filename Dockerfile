FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN useradd --create-home app && mkdir -p /data && chown -R app /data
USER app

EXPOSE 8000
VOLUME ["/data"]
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--preload", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-"]
