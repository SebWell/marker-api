# Marker API

API de conversion PDF vers Markdown structure utilisant [Marker](https://github.com/datalab-to/marker).

## Description

Cette API utilise des modeles de Machine Learning pour :
- Extraire le texte des PDF scannes (OCR)
- Detecter la structure du document (titres, sections)
- Generer du Markdown structure avec `#`, `##`, `###`

## Utilisation

### Endpoint `/convert`

```bash
curl -X POST -F "file=@document.pdf" http://localhost:5000/convert
```

**Reponse** :
```json
{
  "success": true,
  "markdown": "# Titre Principal\n\n## Section 1\n\nContenu...",
  "source": "marker",
  "has_structure": true,
  "pages_count": 5,
  "processing_time_ms": 12500,
  "structure_stats": {
    "h1_count": 1,
    "h2_count": 3,
    "h3_count": 2
  }
}
```

## Installation

### Docker (recommande)

```bash
docker build -t marker-api .
docker run -p 5000:5000 marker-api
```

### Local

```bash
pip install -r requirements.txt
python app.py
```

## Configuration

| Variable | Defaut | Description |
|----------|--------|-------------|
| `PORT` | 5000 | Port d'ecoute |
| `PRELOAD_MODELS` | false | Pre-charger les modeles au demarrage |

## Notes

- **Premier appel lent** : Les modeles ML (~2-3 GB) sont charges au premier appel
- **Memoire** : Necessite ~4-6 GB de RAM
- **GPU** : Supporte CUDA pour acceleration (optionnel)

## Cas d'usage

Utiliser cette API pour :
- PDF scannes (images de documents)
- PDF complexes (tableaux, equations, formulaires)
- Documents ou PyMuPDF4LLM ne detecte pas la structure

Pour les PDF natifs (texte selectionnable), preferez PyMuPDF API avec `/extract-markdown`.
