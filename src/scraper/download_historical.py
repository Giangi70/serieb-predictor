"""Entry point: scarica i CSV storici."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.config import cfg
from betting_core.scraper import download_all
download_all(cfg)
