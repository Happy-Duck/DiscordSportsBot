# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      python3-dev \
      libffi-dev \
      libssl-dev \
      ca-certificates \
      && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

RUN adduser --disabled-password --gecos "" --home /nonexistent --no-create-home --uid 10001 appuser

# Copy the source code into the container (as root).
COPY . .

# Ensure the appuser has write permissions to the entire /app directory,
# especially for the database file that will be created at runtime in /app/src.
RUN chown -R appuser:appuser /app && \
    chmod -R u+w /app/src

# Switch to the non-privileged user to run the application.
USER appuser

# Run the application (module form so the src package imports resolve).
CMD [ "python3", "-m", "src.bot" ]