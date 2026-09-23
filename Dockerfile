# ==========================================
# Stage 1: Build React/Vite Frontend Assets
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /app

# Install Node dependencies
COPY package*.json ./
RUN npm ci

# Copy frontend source and build production bundle
COPY . .
RUN npm run build

# ==========================================
# Stage 2: Production FastAPI Application
# ==========================================
FROM python:3.11-slim
WORKDIR /app

# Install system libraries needed by PostgreSQL client and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy built frontend assets from stage 1 into /app/dist
COPY --from=frontend-builder /app/dist ./dist

# Copy backend source code into /app/backend
COPY backend ./backend

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Start FastAPI server serving both API and frontend SPA
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
