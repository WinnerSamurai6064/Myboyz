FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .

# Upgrade pip first, then install with the legacy resolver
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
