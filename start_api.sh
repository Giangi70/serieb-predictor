#!/bin/bash
set -e

VENV="/home/egiabot/venvs/serieb-predictor"
PROJECT="/home/egiabot/PROJECT/serieb-predictor"
PORT=8002

source "$VENV/bin/activate"

echo "🚀 Avvio API su http://localhost:$PORT (docs: /docs)"
cd "$PROJECT"
PYTHONPATH="$PROJECT" uvicorn src.api:app --host 0.0.0.0 --port "$PORT"
