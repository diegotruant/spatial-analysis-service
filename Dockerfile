FROM python:3.11

WORKDIR /app

# Install system dependencies including Java for FitCSVTool
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bind to Render-provided PORT at runtime.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
