# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures Python output is sent straight to the terminal
ENV PYTHONUNBUFFERED 1

# Install system dependencies, including curl for the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch separately to avoid dependency conflicts
RUN pip install torch==2.1.0 --index-url [https://download.pytorch.org/whl/cpu](https://download.pytorch.org/whl/cpu)

# Install sentence-transformers without its dependencies
RUN pip install sentence-transformers==2.2.2 --no-dependencies

# Install the rest of the Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the spaCy language model
RUN python -m spacy download en_core_web_sm

# Create directory for persistent data
RUN mkdir -p /usr/src/app/data/faiss_index
RUN mkdir -p /usr/src/app/data/output

# Copy the application code into the container
COPY ./app /usr/src/app/app

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0"]
