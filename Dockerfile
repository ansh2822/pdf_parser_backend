FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

WORKDIR /app

COPY requirements.txt .

# Install CPU-only torch first — prevents docling from pulling CUDA version (~2.5 GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining deps, then purge build tools to shrink image
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    poppler-utils \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
