#!/bin/bash
set -e

VENV="/home/egiabot/venvs/serieb-predictor"
PROJECT="/home/egiabot/PROJECT/serieb-predictor"

# Attiva virtualenv
source "$VENV/bin/activate"

# Scarica dati storici se non presenti
if [ ! -f "$PROJECT/data/raw/serie_b_2425.csv" ]; then
    echo "📥 Scarico dati storici..."
    PYTHONPATH="$PROJECT" python "$PROJECT/src/scraper/download_historical.py"
fi

# Addestra il modello se non presente
if [ ! -f "$PROJECT/models/model.joblib" ]; then
    echo "🏋️  Addestro il modello..."
    PYTHONPATH="$PROJECT" python "$PROJECT/src/training/train.py"
fi

echo "🚀 Avvio app su http://localhost:8502"
cd "$PROJECT"
PYTHONPATH="$PROJECT" streamlit run src/ui/app.py --server.port 8502
