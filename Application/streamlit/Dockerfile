# Base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app and .env from the parent directory
COPY . .

# Install python-dotenv to manage .env loading
RUN pip install python-dotenv

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.enableCORS=false"]