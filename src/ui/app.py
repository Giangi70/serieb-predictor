"""Interfaccia Streamlit per il Serie A Predictor."""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.prediction.predict import predict_match
from src.scraper.odds_live import get_upcoming_odds, get_mock_odds
from src.db.storage import init_db, save_prediction, set_result, get_all_predictions, get_roi_stats, get_pending_predictions, save_odds_cache, load_odds_cache, save_strategia_mista, get_strategia_mista, set_result_strategia, get_roi_strategia
from src.db.update_results import auto_update_results
from config.config import ODDS_API_KEY, DATA_PROCESSED, DATA_EXPORTS, MODELS_DIR

init_db()

st.set_page_config(page_title="Serie B Predictor", page_icon="⚽", layout="wide")
st.title("⚽ Serie B Predictor")
st.caption("Predizioni basate sulle quote dei bookmaker — Serie B")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Impostazioni")
    use_mock = st.toggle("Usa dati di esempio (no API key)", value=not bool(ODDS_API_KEY))
    use_kelly = st.toggle(
        "Kelly criterion",
        value=False,
        help="ON: suggerisce quanto scommettere in base all'edge stimato (Kelly). OFF: flat betting (importo fisso)",
    )
    bankroll = None
    if use_kelly:
        bankroll = st.number_input(
            "Bankroll (€)", min_value=10, value=100, step=10,
            help="Il tuo capitale totale da cui calcolare la frazione Kelly",
        )
    st.divider()
    st.subheader("Stato sistema")
    model_ok = (MODELS_DIR / "model.joblib").exists()
    data_ok  = (DATA_PROCESSED / "dataset.csv").exists()
    st.write("🟢 Modello" if model_ok else "🔴 Modello non trovato")
    st.write("🟢 Dataset" if data_ok else "🔴 Dataset non trovato")
    if data_ok:
        df_info = pd.read_csv(DATA_PROCESSED / "dataset.csv")
        st.write(f"📊 {len(df_info)} partite nel dataset")

# ── Tab principali ────────────────────────────────────────────────────────────
tab_pred, tab_manual, tab_update, tab_history, tab_strategia = st.tabs(["🔮 Predizioni giornata", "✏️ Inserimento manuale", "🔄 Aggiorna dataset", "📊 Storico", "🎯 Strategia Mista"])

# ── Tab 1: Predizioni automatiche ────────────────────────────────────────────
with tab_pred:
    st.subheader("Prossima giornata Serie A")

    if not model_ok:
        st.error("Modello non trovato. Esegui prima il training.")
        st.stop()

    cached_matches, cached_at = load_odds_cache()

    col_btn, col_warn = st.columns([1, 3])
    with col_btn:
        load_clicked = st.button("🔄 Carica quote", type="primary", help="Scarica le quote della prossima giornata di Serie A tramite The Odds API")
    with col_warn:
        if cached_at and not use_mock:
            from datetime import datetime, timezone
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(cached_at.replace(" ", "T") + "+00:00")).total_seconds() / 3600
            if age_h > 6:
                st.warning(f"⚠️ Quote vecchie ({int(age_h)}h fa) — consigliamo di ricaricare")
            else:
                st.caption(f"📦 Cache aggiornata {int(age_h * 60)}min fa")

    if load_clicked:
        with st.spinner("Recupero quote..."):
            try:
                if use_mock:
                    matches = get_mock_odds()
                else:
                    matches = get_upcoming_odds()
                    save_odds_cache(matches)
                st.session_state["matches"] = matches
            except Exception as e:
                st.error(f"Errore: {e}")

    matches = st.session_state.get("matches", [])
    if not matches:
        st.info("Clicca 'Carica quote' per vedere le predizioni.")
    else:
        results = []
        for m in matches:
            try:
                pred = predict_match(m["home_team"], m["away_team"], m["odds"])
                # Quota media bookmaker per l'esito predetto
                suffix = pred["prediction"]
                bk_odds = [v for k, v in m["odds"].items() if k.endswith(suffix) and v > 1]
                avg_odds = round(sum(bk_odds) / len(bk_odds), 2) if bk_odds else None

                save_prediction(
                    home_team=m["home_team"],
                    away_team=m["away_team"],
                    prediction=pred["prediction"],
                    prob_h=pred["probs"]["H"],
                    prob_d=pred["probs"]["D"],
                    prob_a=pred["probs"]["A"],
                    value_bet=pred.get("value_bet", False),
                    avg_odds=avg_odds,
                    match_date=m.get("commence_time", "")[:10],
                )
                # Kelly criterion: f = (p*b - (1-p)) / b  dove b = quota - 1
                kelly_stake = None
                if pred.get("value_bet") and avg_odds and avg_odds > 1:
                    p = pred["probs"][pred["prediction"]]
                    b = avg_odds - 1
                    f = (p * b - (1 - p)) / b
                    kelly_stake = round(max(f, 0) * bankroll, 2) if use_kelly else None

                results.append({
                    "Casa":        m["home_team"],
                    "Trasferta":   m["away_team"],
                    "Predizione":  pred["prediction_label"],
                    "P(Casa) %":   f"{pred['probs']['H']*100:.1f}",
                    "P(Pareggio) %": f"{pred['probs']['D']*100:.1f}",
                    "P(Trasferta) %": f"{pred['probs']['A']*100:.1f}",
                    "Confidenza %": f"{pred['confidence']*100:.1f}",
                    "Bookmaker":   len(m["odds"]) // 3,
                    "Value Bet":   "✅" if pred.get("value_bet") else "",
                    **( {"Scommetti (€)": f"{kelly_stake:.2f}" if kelly_stake else ""} if use_kelly else {} ),
                })
            except Exception as e:
                st.warning(f"{m['home_team']} vs {m['away_team']}: {e}")

        if results:
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True, hide_index=True)
            caption = "✅ Value Bet: prob trasferta > 45% e varianza bookmaker bassa (ROI storico +10% su 5 stagioni)"
            if use_kelly:
                caption += f" | 💰 Kelly criterion attivo (bankroll: {bankroll}€)"
            st.caption(caption)

            export_cols = ["Casa", "Trasferta", "Predizione", "P(Casa) %", "P(Pareggio) %", "P(Trasferta) %", "Confidenza %", "Value Bet"]
            if use_kelly and "Scommetti (€)" in df_results.columns:
                export_cols.append("Scommetti (€)")
            csv_bytes = df_results[export_cols].to_csv(index=False).encode("utf-8")

            # Salva su disco in data/exports/
            from datetime import datetime
            DATA_EXPORTS.mkdir(parents=True, exist_ok=True)
            export_filename = f"predizioni_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            export_path = DATA_EXPORTS / export_filename
            export_path.write_bytes(csv_bytes)

            st.download_button(
                "📥 Esporta predizioni CSV",
                data=csv_bytes,
                file_name=export_filename,
                mime="text/csv",
                help=f"Scarica il CSV (salvato anche in data/exports/{export_filename})",
            )
            st.caption(f"💾 Salvato anche in `data/exports/{export_filename}`")

# ── Tab 2: Inserimento manuale ────────────────────────────────────────────────
with tab_manual:
    st.subheader("Inserisci quote manualmente")
    col1, col2 = st.columns(2)
    with col1:
        home = st.text_input("Squadra casa", "Inter")
        away = st.text_input("Squadra trasferta", "Milan")
    with col2:
        st.write("**Quote Bet365**")
        b365h = st.number_input("1 (casa)", min_value=1.01, value=2.10, step=0.05)
        b365d = st.number_input("X (pareggio)", min_value=1.01, value=3.40, step=0.05)
        b365a = st.number_input("2 (trasferta)", min_value=1.01, value=3.20, step=0.05)

    with st.expander("Aggiungi altri bookmaker (opzionale)"):
        c1, c2, c3 = st.columns(3)
        with c1:
            whh = st.number_input("WH 1", min_value=0.0, value=0.0, step=0.05)
            whd = st.number_input("WH X", min_value=0.0, value=0.0, step=0.05)
            wha = st.number_input("WH 2", min_value=0.0, value=0.0, step=0.05)
        with c2:
            psh = st.number_input("PS 1", min_value=0.0, value=0.0, step=0.05)
            psd = st.number_input("PS X", min_value=0.0, value=0.0, step=0.05)
            psa = st.number_input("PS 2", min_value=0.0, value=0.0, step=0.05)

    if st.button("🔮 Predici", type="primary", help="Calcola la predizione (1/X/2) e il filtro value bet per la partita inserita"):
        odds = {"B365H": b365h, "B365D": b365d, "B365A": b365a}
        if whh > 1: odds.update({"WHH": whh, "WHD": whd, "WHA": wha})
        if psh > 1: odds.update({"PSH": psh, "PSD": psd, "PSA": psa})
        try:
            pred = predict_match(home, away, odds)
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Predizione", pred["prediction_label"])
            col_b.metric(f"P({home})", f"{pred['probs']['H']*100:.1f}%")
            col_c.metric("P(Pareggio)", f"{pred['probs']['D']*100:.1f}%")
            col_d.metric(f"P({away})", f"{pred['probs']['A']*100:.1f}%")
        except Exception as e:
            st.error(f"Errore: {e}")

# ── Tab 3: Aggiorna dataset ───────────────────────────────────────────────────
with tab_update:
    st.subheader("Aggiorna dataset e ri-addestra il modello")
    st.info(
        "Dopo ogni giornata puoi scaricare i nuovi risultati e ri-addestrare il modello "
        "per includere le partite più recenti."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Scarica nuovi dati storici", help="Scarica i CSV aggiornati da football-data.co.uk (ultime 5 stagioni). Necessario prima di ri-addestrare il modello"):
            with st.spinner("Download CSV..."):
                try:
                    from src.scraper.download_historical import download_all
                    paths = download_all()
                    st.success(f"Scaricati {len(paths)} file")
                except Exception as e:
                    st.error(f"Errore download: {e}")

    with col2:
        if st.button("🏋️ Ri-addestra modello", help="Ri-addestra il modello XGBoost includendo le partite più recenti. Esegui prima 'Scarica nuovi dati storici'"):
            with st.spinner("Training in corso..."):
                try:
                    from src.training.train import run as train_run
                    # Forza ricalcolo del dataset
                    processed_path = DATA_PROCESSED / "dataset.csv"
                    if processed_path.exists():
                        processed_path.unlink()
                    train_run()
                    st.success("Modello aggiornato!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore training: {e}")

# ── Tab 4: Storico ────────────────────────────────────────────────────────────
with tab_history:
    st.subheader("Storico predizioni")

    if st.button("🔄 Aggiorna risultati", type="primary", help="Cerca nei CSV storici i risultati reali delle partite già giocate e li registra automaticamente nel database"):
        with st.spinner("Cerco risultati nei CSV..."):
            r = auto_update_results()
        if r["updated"] == 0 and r["still_missing"] == 0:
            st.info("Nessuna predizione in attesa di risultato.")
        else:
            if r["updated"]:
                st.success(f"Aggiornati {r['updated']} risultati.")
            if r["still_missing"]:
                st.warning(f"{r['still_missing']} partite non ancora nei CSV (probabilmente non ancora giocate o CSV non aggiornato).")
            with st.expander("Dettagli"):
                for d in r["details"]:
                    st.write(d)
        st.rerun()

    st.divider()

    rows = get_all_predictions()
    if not rows:
        st.info("Nessuna predizione salvata. Carica le quote dalla tab 'Predizioni giornata'.")
    else:
        df_hist = pd.DataFrame(rows)

        # Sezione ROI value bet
        stats = get_roi_stats()
        if stats["n"] > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Value bet con risultato", stats["n"])
            c2.metric("Win rate", f"{stats['win_rate']*100:.1f}%")
            roi_val = stats["roi"]
            c3.metric("ROI reale", f"{roi_val*100:.1f}%" if roi_val is not None else "—",
                      delta_color="normal")
            st.divider()

        # Tabella con possibilità di registrare risultato
        st.write("**Registra risultato reale** (per le partite già giocate)")
        pending = df_hist[df_hist["result"].isna()]
        if not pending.empty:
            sel = st.selectbox(
                "Seleziona partita",
                options=pending["id"].tolist(),
                format_func=lambda i: next(
                    f"{r['home_team']} vs {r['away_team']} ({r['match_date'] or r['created_at']})"
                    for r in rows if r["id"] == i
                ),
            )
            res = st.radio("Risultato reale", ["H", "D", "A"], horizontal=True)
            if st.button("💾 Salva risultato"):
                set_result(sel, res)
                st.success("Risultato salvato!")
                st.rerun()

        st.divider()
        # Tabella completa
        display_cols = ["match_date", "home_team", "away_team", "prediction",
                        "prob_h", "prob_d", "prob_a", "value_bet", "avg_odds", "result"]
        st.dataframe(
            df_hist[display_cols].rename(columns={
                "match_date": "Data", "home_team": "Casa", "away_team": "Trasferta",
                "prediction": "Pred", "prob_h": "P(H)", "prob_d": "P(D)", "prob_a": "P(A)",
                "value_bet": "VB", "avg_odds": "Quota", "result": "Risultato",
            }),
            use_container_width=True, hide_index=True,
        )

# ── Tab 5: Strategia Mista ────────────────────────────────────────────────────
with tab_strategia:
    import numpy as np

    # Parametri strategia (ottimizzati dall'analisi storica)
    N_SAFE       = 9      # partite su cui giocare l'esito più probabile
    N_JOLLY      = 1      # partite su cui giocare la quota più alta
    MIN_GAP      = 0.15   # gap minimo tra prob_max e prob_seconda
    MIN_Q_JOLLY  = 5.0    # quota minima per il jolly
    # Soglia ROI "stagione calda": se il ROI stagionale supera questa soglia → alert
    ROI_ALERT_THRESHOLD = 0.08   # +8% (storico: stagioni calde erano >10%)
    SEASON_START = "2025-08-01"  # inizio stagione corrente

    st.subheader("🎯 Strategia Mista — 9 safe + 1 jolly")
    st.caption(
        f"Parametri: {N_SAFE} partite sull'esito più probabile + {N_JOLLY} jolly (quota > {MIN_Q_JOLLY}) | "
        f"Filtro gap probabilità ≥ {MIN_GAP:.0%} | Alert ROI stagionale > {ROI_ALERT_THRESHOLD:.0%}"
    )

    # ── Monitor ROI stagione corrente ─────────────────────────────────────────
    stats_s = get_roi_strategia(season_start=SEASON_START)
    stats_all = get_roi_strategia()

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Scommesse stagione", stats_s["n"])
    col_b.metric("P&L stagione (€)", f"{stats_s['pl']:+.2f}" if stats_s["n"] else "—")
    roi_s_val = stats_s["roi"]
    col_c.metric(
        "ROI stagione",
        f"{roi_s_val*100:+.1f}%" if roi_s_val is not None else "—",
        delta_color="normal",
    )
    col_d.metric("Scommesse totali", stats_all["n"])

    # Alert stagione calda
    if roi_s_val is not None and roi_s_val >= ROI_ALERT_THRESHOLD and stats_s["n"] >= 20:
        st.success(
            f"🔥 **STAGIONE CALDA** — ROI stagionale {roi_s_val*100:+.1f}% su {stats_s['n']} scommesse. "
            f"Storico: ROI > {ROI_ALERT_THRESHOLD:.0%} indica una stagione con edge reale. "
            f"Considera di aumentare le puntate."
        )
    elif stats_s["n"] >= 20:
        st.info(
            f"📊 ROI stagionale {roi_s_val*100:+.1f}% — mercato efficiente. "
            f"Continua a monitorare: l'alert scatta a ROI > {ROI_ALERT_THRESHOLD:.0%}."
        )
    else:
        st.info(f"📊 Dati insufficienti per il monitor ROI (servono ≥ 20 scommesse, hai {stats_s['n']}).")

    st.divider()

    # ── Segnali giornata corrente ─────────────────────────────────────────────
    st.subheader("Segnali prossima giornata")

    QUOTE_COLS_APP = {
        "H": ["B365H", "WHH", "IWH", "PSH", "VCH"],
        "D": ["B365D", "WHD", "IWD", "PSD", "VCD"],
        "A": ["B365A", "WHA", "IWA", "PSA", "VCA"],
    }

    def _quota_media(odds: dict, esito: str) -> float | None:
        vals = [v for k, v in odds.items() if k.endswith(esito) and v > 1]
        return round(sum(vals) / len(vals), 2) if vals else None

    def _prob_gap(probs: dict) -> float:
        sorted_p = sorted(probs.values(), reverse=True)
        return sorted_p[0] - sorted_p[1]

    def _max_quota(odds: dict) -> tuple[str, float]:
        best_esito, best_q = "H", 0.0
        for esito in ["H", "D", "A"]:
            vals = [v for k, v in odds.items() if k.endswith(esito) and v > 1]
            if vals and max(vals) > best_q:
                best_q = max(vals)
                best_esito = esito
        return best_esito, best_q

    if st.button("🔄 Calcola segnali giornata", type="primary"):
        cached_matches, _ = load_odds_cache()
        if use_mock:
            raw_matches = get_mock_odds()
        elif cached_matches:
            raw_matches = cached_matches
        else:
            try:
                raw_matches = get_upcoming_odds()
                save_odds_cache(raw_matches)
            except Exception as e:
                st.error(f"Errore quote: {e}")
                raw_matches = []

        if raw_matches:
            # Calcola prob e gap per ogni partita
            enriched = []
            for m in raw_matches:
                odds = m["odds"]
                probs = {
                    "H": 1 / _quota_media(odds, "H") if _quota_media(odds, "H") else None,
                    "D": 1 / _quota_media(odds, "D") if _quota_media(odds, "D") else None,
                    "A": 1 / _quota_media(odds, "A") if _quota_media(odds, "A") else None,
                }
                if None in probs.values():
                    continue
                tot = sum(probs.values())
                probs = {k: v / tot for k, v in probs.items()}
                gap = _prob_gap(probs)
                best_esito = max(probs, key=probs.get)
                best_quota = _quota_media(odds, best_esito)
                jolly_esito, jolly_quota = _max_quota(odds)
                enriched.append({
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "match_date": m.get("commence_time", "")[:10],
                    "probs": probs,
                    "gap": gap,
                    "best_esito": best_esito,
                    "best_quota": best_quota,
                    "jolly_esito": jolly_esito,
                    "jolly_quota": jolly_quota,
                })

            # Seleziona safe: gap >= MIN_GAP, ordinate per prob_max desc
            pool_safe = sorted(
                [e for e in enriched if e["gap"] >= MIN_GAP],
                key=lambda x: x["probs"][x["best_esito"]], reverse=True
            )[:N_SAFE]

            # Seleziona jolly: quota >= MIN_Q_JOLLY, ordinate per jolly_quota desc
            pool_jolly = sorted(
                [e for e in enriched if e["jolly_quota"] >= MIN_Q_JOLLY],
                key=lambda x: x["jolly_quota"], reverse=True
            )[:N_JOLLY]

            if not pool_safe:
                st.warning(f"Nessuna partita con gap ≥ {MIN_GAP:.0%}. Prova ad abbassare il threshold.")
            else:
                st.write(f"**✅ {len(pool_safe)} scommesse SAFE** — gioca l'esito più probabile:")
                safe_rows = [{
                    "Casa": e["home_team"], "Trasferta": e["away_team"],
                    "Esito": e["best_esito"],
                    "Prob %": f"{e['probs'][e['best_esito']]*100:.1f}",
                    "Gap %": f"{e['gap']*100:.1f}",
                    "Quota media": e["best_quota"],
                } for e in pool_safe]
                st.dataframe(pd.DataFrame(safe_rows), use_container_width=True, hide_index=True)

            if not pool_jolly:
                st.warning(f"Nessuna partita con quota jolly ≥ {MIN_Q_JOLLY}.")
            else:
                st.write(f"**🎲 {len(pool_jolly)} scommessa JOLLY** — gioca la quota più alta:")
                jolly_rows = [{
                    "Casa": e["home_team"], "Trasferta": e["away_team"],
                    "Esito jolly": e["jolly_esito"],
                    "Quota jolly": e["jolly_quota"],
                } for e in pool_jolly]
                st.dataframe(pd.DataFrame(jolly_rows), use_container_width=True, hide_index=True)

            # Salva nel DB
            scommesse_db = [
                {
                    "match_date": e["match_date"], "home_team": e["home_team"],
                    "away_team": e["away_team"], "tipo": "safe",
                    "esito": e["best_esito"], "quota": e["best_quota"],
                    "prob_gap": e["gap"],
                }
                for e in pool_safe
            ] + [
                {
                    "match_date": e["match_date"], "home_team": e["home_team"],
                    "away_team": e["away_team"], "tipo": "jolly",
                    "esito": e["jolly_esito"], "quota": e["jolly_quota"],
                    "prob_gap": e["gap"],
                }
                for e in pool_jolly
            ]
            save_strategia_mista(scommesse_db)
            st.caption("💾 Scommesse salvate nel DB per il tracking ROI.")

    st.divider()

    # ── Storico strategia mista + registra risultati ──────────────────────────
    st.subheader("Storico scommesse strategia mista")
    rows_sm = get_strategia_mista()
    if not rows_sm:
        st.info("Nessuna scommessa registrata. Clicca 'Calcola segnali giornata'.")
    else:
        df_sm = pd.DataFrame(rows_sm)

        # Registra risultato
        pending_sm = df_sm[df_sm["result"].isna()]
        if not pending_sm.empty:
            with st.expander("📝 Registra risultati reali"):
                sel_id = st.selectbox(
                    "Partita",
                    options=pending_sm["id"].tolist(),
                    format_func=lambda i: next(
                        f"{r['home_team']} vs {r['away_team']} ({r['match_date']}) [{r['tipo']}]"
                        for r in rows_sm if r["id"] == i
                    ),
                )
                res_sm = st.radio("Risultato", ["H", "D", "A"], horizontal=True, key="res_sm")
                if st.button("💾 Salva", key="save_sm"):
                    set_result_strategia(sel_id, res_sm)
                    st.success("Salvato!")
                    st.rerun()

        display_sm = ["match_date", "home_team", "away_team", "tipo", "esito", "quota", "prob_gap", "result"]
        st.dataframe(
            df_sm[display_sm].rename(columns={
                "match_date": "Data", "home_team": "Casa", "away_team": "Trasferta",
                "tipo": "Tipo", "esito": "Esito", "quota": "Quota",
                "prob_gap": "Gap", "result": "Risultato",
            }),
            use_container_width=True, hide_index=True,
        )
