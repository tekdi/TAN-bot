# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt install build-essential --fix-missing -y

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"] 