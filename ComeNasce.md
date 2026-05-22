# Come nasce Serie B Predictor

## Origine

Progetto gemello di `seriea-predictor`, creato il 22/05/2026 come secondo componente
dell'ecosistema Betting multi-sport (vedi `BettingEcosystem.md`).

## Motivazione

La Serie B è un mercato di nicchia: meno scommettitori, bookmaker meno precisi.
La CV accuracy del modello (~43%) è inferiore alla Serie A (~51%), il che conferma
che i bookmaker prezzano la Serie B con meno precisione — potenzialmente più edge.

## Costruzione (22/05/2026)

Clone di `seriea-predictor` con le seguenti modifiche:
- `config/config.py`: `I2.csv` invece di `I1.csv`, endpoint `soccer_italy_serie_b`, DB `serieb.db`
- `src/scraper/download_historical.py`: salva come `serie_b_XXXX.csv`
- `src/training/preprocess.py`: legge `serie_b_XXXX.csv`
- `src/ui/app.py`: titolo "Serie B Predictor"
- `start.sh`: virtualenv `serieb-predictor`, porta 8502

Dati scaricati: 9 stagioni (1617→2425), 3534 partite.
Modello addestrato: CV accuracy 43.2% ± 1.1%.

## Stato attuale

| Componente | Stato |
|---|---|
| Download dati storici (9 stagioni) | ✅ |
| Preprocessing + training | ✅ (43.2% CV accuracy) |
| UI Streamlit (porta 8502) | ✅ |
| Quote live Serie B | ✅ (The Odds API) |
| Strategia mista 9+1 | ✅ (ereditata) |
| Analisi backtest Serie B | 🔲 Da fare |

## Prossimi passi

1. Eseguire `notebooks/analisi_strategia_mista.py` sui dati Serie B per calibrare
   i parametri (gap threshold, min_quota_jolly) specifici per questo campionato
2. Aggiungere layer API REST (FastAPI) per l'integrazione con il betting-agent
