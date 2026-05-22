# Serie B Predictor

Predice l'esito (1/X/2) delle partite di Serie B usando le quote dei bookmaker come feature di input per un modello ML.

Progetto gemello di [seriea-predictor](https://github.com/Giangi70/seriea-predictor), adattato per la Serie B italiana.

## Motivazione

La Serie B è un mercato meno seguito rispetto alla Serie A: meno scommettitori, meno attenzione dei bookmaker, modelli interni meno raffinati. Questo si traduce in più inefficienze potenziali da sfruttare.

**CV accuracy modello: ~43%** (vs ~51% Serie A) — la Serie B è più imprevedibile, il che conferma che i bookmaker la prezzano con meno precisione.

## Stack

| Componente | Tecnologia |
|---|---|
| Linguaggio | Python 3.11+ |
| ML | XGBoost + scikit-learn |
| UI | Streamlit (porta 8502) |
| Database locale | SQLite |
| Quote live | The Odds API (`soccer_italy_serie_b`) |
| Dati storici | football-data.co.uk (`I2.csv`) |

## Struttura progetto

```
serieb-predictor/
├── config/config.py           # Configurazione (I2.csv, endpoint Serie B)
├── data/raw/                  # CSV storici serie_b_XXXX.csv
├── data/processed/            # Dataset preprocessato
├── models/model.joblib        # Modello XGBoost addestrato
├── notebooks/                 # Analisi esplorative (ereditate da Serie A)
├── src/                       # Codice sorgente (identico a Serie A)
└── start.sh                   # Avvio rapido (porta 8502)
```

## Avvio rapido

```bash
./start.sh
```

Apre l'app su `http://localhost:8502`.

## Setup manuale

```bash
# Virtualenv
python3 -m venv /home/egiabot/venvs/serieb-predictor
source /home/egiabot/venvs/serieb-predictor/bin/activate
pip install -r requirements.txt

# Dati e modello
PYTHONPATH=. python src/scraper/download_historical.py
PYTHONPATH=. python src/training/train.py

# App
PYTHONPATH=. streamlit run src/ui/app.py --server.port 8502
```

## Dati storici

Fonte: [football-data.co.uk](https://www.football-data.co.uk/italym.php) — file `I2.csv`

9 stagioni disponibili: 2016/17 → 2024/25 (3534 partite dopo preprocessing).

## Differenze rispetto a seriea-predictor

| Parametro | Serie A | Serie B |
|---|---|---|
| File CSV | `I1.csv` | `I2.csv` |
| API endpoint | `soccer_italy_serie_a` | `soccer_italy_serie_b` |
| Porta Streamlit | 8501 | 8502 |
| CV accuracy | ~51% | ~43% |
| DB file | `seriea.db` | `serieb.db` |

## Parte dell'ecosistema Betting

Questo progetto fa parte di un ecosistema multi-sport. Vedi `/home/egiabot/PROJECT/BettingEcosystem.md`.
