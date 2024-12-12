FROM python:3.11

WORKDIR /app


COPY requirements.txt .

# for dev mode, comment before production
# COPY dev_requirements.txt .

# for dev mode, uncomment before production
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /app

# Install dependencies for the part that needs llama-index-core and openai >= 1.1.0
# COPY requirements1.txt .
# RUN pip install --no-cache-dir -r requirements1.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]