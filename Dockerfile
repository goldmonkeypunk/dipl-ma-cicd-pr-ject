# ──────────────────────────────────────────────────────────────
# Базовий імідж + оновлення pip
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ──────────────────────────────────────────────────────────────
# Встановлюємо продакшн-та Dev-залежності
# ──────────────────────────────────────────────────────────────
COPY requirements.txt requirements.txt
COPY requirements-dev.txt requirements-dev.txt

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements-dev.txt

# ──────────────────────────────────────────────────────────────
# Копіюємо код застосунку
# ──────────────────────────────────────────────────────────────
COPY . .

# ──────────────────────────────────────────────────────────────
# Gunicorn + gevent — без абсолютного шляху, він у $PATH
# ──────────────────────────────────────────────────────────────
CMD ["gunicorn", "-k", "gevent", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
