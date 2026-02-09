FROM python:3.11

WORKDIR /app

# Install system dependencies including Java for FitCSVTool
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use exec form, hardcoded to 8080 which matches Cloud Run default
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
