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
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY app.py .

# Variables d'environnement
ENV PORT=5000
ENV PRELOAD_MODELS=false

# Expose le port
EXPOSE 5000

# Commande de demarrage avec gunicorn
# Timeout eleve car le premier appel charge les modeles (~2-3min)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "--workers", "1", "app:app"]
