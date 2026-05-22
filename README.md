# Serie B Predictor

Predice l'esito (1/X/2) delle partite di **Serie B italiana** usando le quote dei bookmaker come feature per un modello ML (XGBoost).

Parte dell'ecosistema [Betting](https://github.com/Giangi70/betting-core) multi-sport.

## Quick Start

```bash
git clone https://github.com/Giangi70/serieb-predictor
cd serieb-predictor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # inserisci ODDS_API_KEY (opzionale)
./start.sh
```

L'app si apre su **http://localhost:8502**

## Dati

- **Storici**: [football-data.co.uk](https://www.football-data.co.uk) — 9 stagioni (2016/17→2024/25), ~3500 partite
- **Quote live**: [The Odds API](https://the-odds-api.com) — endpoint `soccer_italy_serie_b`
- **CV accuracy modello**: ~43% (mercato meno efficiente della Serie A → più edge potenziale)

## Funzionalità

| Tab | Descrizione |
|---|---|
| 🔮 Predizioni giornata | Quote live → predizioni 1/X/2 con probabilità |
| ✏️ Inserimento manuale | Inserisci quote a mano per una singola partita |
| 🔄 Aggiorna dataset | Scarica nuovi dati e ri-addestra il modello |
| 📊 Storico | Predizioni passate, risultati reali, ROI value bet |
| 🎯 Strategia Mista | Segnali 9-safe+1-jolly con monitor ROI stagionale |

## Ecosistema

Questo progetto fa parte di un ecosistema multi-sport:

| Progetto | Campionato | Porta |
|---|---|---|
| [seriea-predictor](https://github.com/Giangi70/seriea-predictor) | Serie A Italia | 8501 |
| [serieb-predictor](https://github.com/Giangi70/serieb-predictor) | Serie B Italia | 8502 |
| [laliga2-predictor](https://github.com/Giangi70/laliga2-predictor) | La Liga 2 Spagna | 8503 |
| [bundesliga2-predictor](https://github.com/Giangi70/bundesliga2-predictor) | Bundesliga 2 Germania | 8504 |
| [betting-core](https://github.com/Giangi70/betting-core) | Libreria condivisa | — |
