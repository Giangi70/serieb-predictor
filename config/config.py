"""Configurazione centralizzata del progetto."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
DATA_EXPORTS = BASE_DIR / "data" / "exports"
MODELS_DIR = BASE_DIR / "models"

# Stagioni Serie B su football-data.co.uk
SEASONS = ["1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324", "2425"]
FOOTBALL_DATA_URL = "https://www.football-data.co.uk/mmz4281/{season}/I2.csv"

# Quote bookmaker da usare come feature
BOOKMAKERS = {
    "B365": "Bet365",
    "WH":   "William Hill",
    "IW":   "Interwetten",
    "PS":   "Pinnacle",
    "VC":   "VC Bet",
}

# The Odds API
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/soccer_italy_serie_b/odds"

# Database
DB_PATH = BASE_DIR / "data" / "serieb.db"
