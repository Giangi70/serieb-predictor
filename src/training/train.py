"""Entry point: addestra il modello."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import cfg
from betting_core.training import run
run(cfg)
