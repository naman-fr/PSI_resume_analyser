# Stage 1: Build React static assets
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build FastAPI server and python environment
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (poppler-utils is required for pdf extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install fastapi uvicorn python-multipart directly (in case they are not in requirements)
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy built frontend static files from stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy the backend source files
COPY . .

# Expose HuggingFace default port
EXPOSE 7860

# Run uvicorn application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
