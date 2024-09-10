# Use the official Python 3.12 base image
FROM python:3.12-slim

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    pip install uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Create a directory for the data
RUN mkdir /data

ENV X_DATA_DIR=/data

# Copy the project files to the container
COPY src src/
COPY static static/
COPY templates templates/
COPY app.py .
COPY pyproject.toml .
# Only reason this is here is because uv reads the whole pyproject.toml file
# and that expects README.md for the description
COPY README.md .
COPY uv.lock .

# Install the project dependencies
RUN uv sync --frozen --no-dev

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--ssl-keyfile", "/data/.ssl/x-remove.cc.key", "--ssl-certfile", "/data/.ssl/x-remove.cc.crt"]
