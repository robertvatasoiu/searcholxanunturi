FROM python:3.10-slim

WORKDIR /app

# Install system curl and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8000"]
