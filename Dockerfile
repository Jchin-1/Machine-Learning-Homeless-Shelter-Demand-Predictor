# Use Python 3.11 slim image to avoid compilation issues with newer Python versions
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# CRUCIAL: Install numpy<2.0.0 FIRST to ensure correct version
RUN pip install --no-cache-dir "numpy<2.0.0"

# Copy requirements.txt and install all dependencies
# This ensures scipy, scikit-learn, pandas, and other packages use numpy<2.0.0
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly copy the Data folder (required for model training)
COPY Data /app/Data

# Copy all other project files into the container
COPY . .

# DEBUG: Verify Data folder exists and show contents
RUN echo "=== CHECKING FOR DATA FOLDER ===" && \
    if [ -d "/app/Data" ]; then \
        echo "[OK] Data folder found at /app/Data"; \
        echo "Contents:"; \
        ls -lR /app/Data; \
    else \
        echo "[ERROR] Data folder NOT FOUND at /app/Data"; \
        echo "Full directory listing:"; \
        ls -laR /app; \
    fi && \
    echo "=== END DATA FOLDER CHECK ===" 

# CRUCIAL: Train the model during build using the correct NumPy version
# This re-pickles the model with the right dependencies
RUN python mlmodel.py

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:80/api/health')" || exit 1

# Start the FastAPI application
CMD ["uvicorn", "web_app.main:app", "--host", "0.0.0.0", "--port", "80"]
