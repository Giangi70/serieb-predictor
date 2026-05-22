"""Scarica i CSV storici della Serie B da football-data.co.uk."""
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import SEASONS, FOOTBALL_DATA_URL, DATA_RAW


def download_season(season: str) -> Path:
    """Scarica il CSV di una stagione e lo salva in data/raw/.

    Args:
        season: Codice stagione (es. '2324' per 2023/24)

    Returns:
        Path del file salvato.

    Raises:
        requests.HTTPError: Se il download fallisce.
    """
    url = FOOTBALL_DATA_URL.format(season=season)
    dest = DATA_RAW / f"serie_b_{season}.csv"

    if dest.exists():
        print(f"[SKIP] {dest.name} già presente")
        return dest

    print(f"[DOWN] {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    print(f"[OK]   Salvato {dest.name} ({len(response.content) // 1024} KB)")
    return dest


def download_all() -> list[Path]:
    """Scarica tutte le stagioni configurate."""
    paths = []
    for season in SEASONS:
        try:
            paths.append(download_season(season))
        except requests.HTTPError as e:
            print(f"[ERR]  Stagione {season}: {e}")
    return paths


if __name__ == "__main__":
    downloaded = download_all()
    print(f"\nTotale: {len(downloaded)} file in {DATA_RAW}")
