"""App Streamlit — Serie A Predictor."""
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.config import cfg
from betting_core.ui.components import (
    render_sidebar, render_tab_predictions, render_tab_manual,
    render_tab_update, render_tab_history, render_tab_strategy,
)
from betting_core.storage import init_db

init_db(cfg)

st.set_page_config(page_title=f"{cfg.name} Predictor", page_icon="⚽", layout="wide")
st.title(f"⚽ {cfg.name} Predictor")
st.caption("Predizioni basate sulle quote dei bookmaker")

use_mock, use_kelly, bankroll = render_sidebar(cfg)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔮 Predizioni giornata", "✏️ Inserimento manuale",
    "🔄 Aggiorna dataset", "📊 Storico", "🎯 Strategia Mista",
])

with tab1: render_tab_predictions(cfg, use_mock, use_kelly, bankroll)
with tab2: render_tab_manual(cfg)
with tab3: render_tab_update(cfg)
with tab4: render_tab_history(cfg)
with tab5: render_tab_strategy(cfg, use_mock)
