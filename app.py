"""
API de conversion PDF -> Markdown avec Marker
Pour PDF scannes et documents complexes
Utilise des modeles ML pour OCR + detection de structure
"""

from flask import Flask, request, jsonify
import tempfile
import os
import time
import requests
from urllib.parse import urlparse

# Configuration pour CPU (VPS sans GPU)
# Forcer l'utilisation du CPU
os.environ["TORCH_DEVICE"] = "cpu"
# Utiliser ocrmypdf (plus rapide que surya sur CPU)
os.environ["OCR_ENGINE"] = "ocrmypdf"

app = Flask(__name__)

# Variables globales pour les modeles (charges une seule fois)
converter = None
models_loaded = False
models_loading = False


def get_converter():
    """
    Charge le convertisseur Marker avec ses modeles.
    Les modeles sont charges une seule fois au premier appel.
    """
    global converter, models_loaded, models_loading

    if models_loaded and converter is not None:
        return converter

    if models_loading:
        # Attendre que le chargement soit termine
        while models_loading:
            time.sleep(0.5)
        return converter

    models_loading = True
    try:
        print("Chargement des modeles Marker...")
        start_time = time.time()

        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        model_dict = create_model_dict()
        converter = PdfConverter(artifact_dict=model_dict)

        elapsed = time.time() - start_time
        print(f"Modeles charges en {elapsed:.1f}s")

        models_loaded = True
        return converter

    except Exception as e:
        print(f"Erreur chargement modeles: {e}")
        models_loading = False
        raise


def download_pdf_from_url(url, timeout=120):
    """
    Télécharge un PDF depuis une URL.

    Args:
        url: URL du PDF
        timeout: Timeout en secondes (défaut: 120 pour gros PDFs)

    Returns:
        bytes: Contenu du PDF
    """
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"URL invalide: schéma '{parsed.scheme}' non supporté")

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    return response.content


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Marker PDF to Markdown API",
        "version": "1.1.0",
        "description": "Conversion PDF scannés -> Markdown structuré via ML",
        "endpoints": {
            "/convert": "POST - Convertir un PDF en Markdown (multipart ou URL)",
            "/health": "GET - Vérifier l'état du service"
        },
        "input_methods": {
            "multipart": "Envoyer un fichier via 'file' (multipart/form-data)",
            "url": "Envoyer une URL de PDF dans JSON {'url': 'https://...'}"
        },
        "note": "Premier appel peut être lent (chargement des modèles ~2-3 GB)"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "engine": "marker",
        "models_loaded": models_loaded
    })


@app.route("/convert", methods=["POST"])
def convert():
    """
    Convertit un PDF en Markdown structuré.

    Accepte:
    - multipart/form-data avec fichier 'file'
    - JSON avec 'url' pour télécharger le PDF depuis une URL

    Retourne:
    - markdown: Texte au format Markdown avec structure (#, ##, ###)
    - source: "marker"
    - has_structure: True si des titres ont été détectés
    - pages_count: Nombre de pages traitées
    """
    try:
        pdf_content = None

        # Option 1: Fichier uploadé
        if "file" in request.files:
            file = request.files["file"]
            if not file.filename:
                return jsonify({"error": "Nom de fichier vide"}), 400
            pdf_content = file.read()

        # Option 2: URL dans JSON
        elif request.is_json and "url" in request.json:
            url = request.json["url"]
            pdf_content = download_pdf_from_url(url)

        else:
            return jsonify({
                "error": "Aucun fichier fourni",
                "usage": "Envoyez un PDF via 'file' (multipart) ou via 'url' (JSON)"
            }), 400

        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        try:
            start_time = time.time()

            # Obtenir le convertisseur (charge les modeles si necessaire)
            conv = get_converter()

            # Conversion avec Marker
            rendered = conv(tmp_path)

            processing_time = time.time() - start_time

            # Extraire le markdown
            markdown_text = rendered.markdown if hasattr(rendered, 'markdown') else str(rendered)

            # Compter les headers pour verifier la structure
            h1_count = markdown_text.count('\n# ') + (1 if markdown_text.startswith('# ') else 0)
            h2_count = markdown_text.count('\n## ')
            h3_count = markdown_text.count('\n### ')
            has_structure = (h1_count + h2_count + h3_count) > 0

            # Nombre de pages
            pages_count = len(rendered.pages) if hasattr(rendered, 'pages') else None

            return jsonify({
                "success": True,
                "markdown": markdown_text,
                "source": "marker",
                "has_structure": has_structure,
                "pages_count": pages_count,
                "processing_time_ms": int(processing_time * 1000),
                "structure_stats": {
                    "h1_count": h1_count,
                    "h2_count": h2_count,
                    "h3_count": h3_count
                }
            })

        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    # Option: pre-charger les modeles au demarrage
    preload = os.getenv("PRELOAD_MODELS", "false").lower() == "true"
    if preload:
        print("Pre-chargement des modeles...")
        get_converter()

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
