FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the application
COPY praier/ ./praier/
COPY README.md LICENSE ./

# Create a non-root user
RUN useradd --create-home --shell /bin/bash praier
USER praier

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PRAIER_LOG_LEVEL=INFO

# Expose health check port (if needed)
EXPOSE 8080

# Default command
CMD ["praier", "monitor"]