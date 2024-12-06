FROM apache/airflow:2.10.2-python3.10

USER root

# Install Chromium and matching ChromeDriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    git git-lfs unzip wget curl gnupg2 xvfb fonts-liberation xdg-utils \
    libnss3 libgconf-2-4 libfontconfig1 libglib2.0-0 libx11-xcb1 \
    libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 libcups2 \
    libxrandr2 libasound2 libatk1.0-0 libgtk-3-0 libgbm1 \
    libssl-dev libffi-dev build-essential binutils \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*


# Set permissions for /tmp/gaia directory
RUN mkdir -p /tmp/gaia && \
    chown -R airflow /tmp/gaia && \
    chmod -R 775 /tmp/gaia

# Copy requirements.txt and .env file
COPY requirements.txt /requirements.txt

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Switch to airflow user
USER airflow

# Install Python packages
RUN pip install --no-cache-dir -r /requirements.txt
