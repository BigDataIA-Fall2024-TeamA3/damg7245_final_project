FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    tesseract-ocr \
    poppler-utils \
    libpoppler-cpp-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy and install FastAPI dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
<<<<<<< HEAD
WORKDIR /app

# Install dependencies for the part that needs llama-index-core and openai >= 1.1.0
# COPY requirements1.txt .
# RUN pip install --no-cache-dir -r requirements1.txt
RUN pip install openai==0.28.0
RUN pip install tavily-python==0.5.0
=======

>>>>>>> 11113456499843bd96616345e5448c707891a986
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4000"]