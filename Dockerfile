# --- Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Final Image ---
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Enable the Debian 'contrib' component (ttf-mscorefonts-installer lives there)
# and auto-accept its EULA so the build is non-interactive.
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/^Components: main$/Components: main contrib/' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's/ main$/ main contrib/' /etc/apt/sources.list; \
    fi; \
    echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" \
        | debconf-set-selections

# Install system dependencies for HarfBuzz and font processing.
# Western fonts so LibreOffice preserves the document's typeface instead of
# substituting DejaVu Serif: real MS core fonts (Arial/Times/Courier/Georgia/
# Verdana/...) plus the metric-compatible families that cover Calibri (Carlito)
# and Cambria (Caladea), which have no MS installer.
RUN apt-get update && apt-get install -y \
    redis-server \
    libharfbuzz-dev \
    libfreetype6-dev \
    libreoffice-writer \
    libreoffice-java-common \
    fontconfig \
    fonts-liberation \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    ttf-mscorefonts-installer \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-tel \
    tesseract-ocr-tam \
    tesseract-ocr-ben \
    tesseract-ocr-guj \
    tesseract-ocr-kan \
    tesseract-ocr-mal \
    tesseract-ocr-ori \
    tesseract-ocr-pan \
    tesseract-ocr-san \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose port
EXPOSE 8000

# Default command (uses start.sh which launches worker + api)
CMD ["/bin/bash", "start.sh"]
