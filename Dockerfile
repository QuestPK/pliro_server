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
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Wait for DB before running migrations
COPY ./wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# Expose Flask port
EXPOSE 8000

# Start services
ENTRYPOINT ["/wait-for-it.sh", "db", "--"]
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]
