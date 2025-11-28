"""
API de conversion PDF -> Markdown avec Marker
Pour PDF scannes et documents complexes
Utilise des modeles ML pour OCR + detection de structure
"""

from flask import Flask, request, jsonify
import tempfile
import os
import time

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


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Marker PDF to Markdown API",
        "version": "1.0.0",
        "description": "Conversion PDF scannes -> Markdown structure via ML",
        "endpoints": {
            "/convert": "POST - Convertir un PDF en Markdown structure",
            "/health": "GET - Verifier l'etat du service"
        },
        "note": "Premier appel peut etre lent (chargement des modeles ~2-3 GB)"
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
    Convertit un PDF en Markdown structure.

    Accepte:
    - multipart/form-data avec fichier 'file'

    Retourne:
    - markdown: Texte au format Markdown avec structure (#, ##, ###)
    - source: "marker"
    - has_structure: True si des titres ont ete detectes
    - pages_count: Nombre de pages traitees
    """
    try:
        # Verifier qu'un fichier est fourni
        if "file" not in request.files:
            return jsonify({
                "error": "Aucun fichier fourni",
                "usage": "Envoyez un PDF via 'file' (multipart/form-data)"
            }), 400

        file = request.files["file"]

        if not file.filename:
            return jsonify({
                "error": "Nom de fichier vide"
            }), 400

        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            file.save(tmp.name)
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
