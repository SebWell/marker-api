FROM python:3.11-slim

WORKDIR /app

# Dependances systeme pour Marker (OpenCV, etc.)
# + tesseract et ocrmypdf pour OCR CPU optimise
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    ocrmypdf \
    ghostscript \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY app.py .

# Variables d'environnement
ENV PORT=5000
ENV PRELOAD_MODELS=true

# Expose le port
EXPOSE 5000

# Healthcheck (start-period eleve: chargement modeles ~2-3 min)
HEALTHCHECK --interval=30s --timeout=30s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Demarrage avec gunicorn
# --preload: charge l'app (et les modeles) avant de forker le worker
# --timeout 600: 10 min max par requete (gros PDFs)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "--workers", "1", "--preload", "app:app"]
