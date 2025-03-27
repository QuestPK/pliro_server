# Use official Python image
FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies (including PostgreSQL client)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/static && touch /app/static/.keep


# Copy the rest of the application
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]