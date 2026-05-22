# Analisi Value Betting — Serie A Predictor

Documento che raccoglie il ragionamento strategico e i risultati empirici dell'analisi value betting sui dati storici (5 stagioni Serie A, 1898 partite).

---

## L'obiettivo

Non massimizzare l'accuratezza delle predizioni, ma trovare **situazioni storicamente profittevoli**: scommesse dove la quota offerta è sistematicamente più alta della probabilità reale dell'evento (**value betting**).

L'obiettivo operativo è costruire un portafoglio di scommesse tale che, scommettendo X€ in totale, la probabilità di ottenere Y€ con Y > X sia elevata — privilegiando la sicurezza rispetto all'entità della vincita.

---

## Il ragionamento strategico

### Ci fidiamo dei bookmaker
I bookmaker usano modelli avanzati. Se sbagliassero sistematicamente, perderebbero denaro. Le loro quote sono già la migliore stima disponibile della probabilità reale.

**Non cerchiamo di battere il bookmaker** — cerchiamo le partite dove il bookmaker è più affidabile, e ci scommettiamo sopra sapendo che la sua stima è più precisa del solito.

### Dove può esserci un edge
- **Divergenza bassa tra bookmaker** → tutti concordano, segnale forte e affidabile
- **Quote sulla trasferta sistematicamente alte** → il pubblico scommette sulla casa, il bookmaker abbassa le quote casa e lascia valore sulla trasferta

### Il filtro operativo
```
prob_esito > soglia  AND  std_esito < soglia  →  scommessa candidata
EV = win_rate_storica × quota_media - 1 > 0  →  valore atteso positivo
```

### Glossario
- **H / A / D** — Home (casa) / Away (trasferta) / Draw (pareggio)
- **prob_H/A/D** — probabilità implicita media tra bookmaker, con vig rimosso
- **std_H/A/D** — deviazione standard delle quote tra bookmaker (misura di accordo/disaccordo)
- **divergence** — differenza massima tra la quota più alta e più bassa tra bookmaker
- **EV (Expected Value)** — valore atteso: `win_rate × quota - 1`. Se > 0, la scommessa è profittevole nel lungo periodo
- **ROI** — Return on Investment: profitto netto / capitale investito
- **vig (overround)** — margine del bookmaker: la somma delle probabilità implicite di 1+X+2 è sempre > 100%

---

## Risultati empirici — Filtro base (11/05/2026)

Script: `notebooks/analisi_value_betting.py`
Dataset: 1898 partite, stagioni 2020/21 → 2024/25

### Accuratezza baseline bookmaker

| Predizione | Accuratezza | Partite |
|---|---|---|
| Globale | **53.8%** | 1898 |
| Quando predice H | 54.0% | 1163 |
| Quando predice A | 53.5% | 734 |
| Quando predice D | 100% | 1 (quasi mai predetto) |

> Il bookmaker non predice quasi mai il pareggio come esito più probabile.

### Calibrazione per fascia di probabilità (esito H)

| Fascia prob_H | Partite | Win rate reale | Quota media B365 | EV |
|---|---|---|---|---|
| < 35% | 721 | 19.6% | 4.42 | -0.134 |
| 35–45% | 367 | 39.0% | 2.36 | -0.079 |
| 45–55% | 293 | 47.4% | 1.89 | -0.105 |
| 55–65% | 225 | 57.8% | 1.60 | -0.078 |
| **65–75%** | **207** | **74.4%** | **1.37** | **+0.017 ✅** |
| > 75% | 85 | 77.6% | 1.21 | -0.062 |

### Effetto della varianza tra bookmaker

| Quartile std_H | Accuratezza bookmaker |
|---|---|
| Q1 (bassa) | **60.5% ✅** |
| Q2 | 50.1% |
| Q3 | 44.9% |
| Q4 (alta) | 59.8% |

### La scoperta principale: il valore è sulla trasferta (A)

Tutti i segmenti con ROI positivo riguardano l'esito **A**. La casa ha sempre ROI negativo nonostante win rate simile — le quote sulla casa sono sistematicamente più basse perché il pubblico ci scommette sopra.

### Top segmenti con ROI positivo

| Esito | prob min | std max | Partite | Win rate | ROI | P&L |
|---|---|---|---|---|---|---|
| A | >70% | Q75 | 28 | 92.9% | **+0.198** | +5.5€ |
| **A** | **>45%** | **Q33** | **393** | **66.2%** | **+0.102** | **+40.0€** |
| A | >55% | Q33 | 220 | 71.8% | +0.093 | +20.5€ |
| A | >50% | Q33 | 316 | 67.7% | +0.080 | +25.3€ |

### Filtro operativo scelto

```
prob_A > 0.45  AND  std_A < 0.0417  →  ✅ Value Bet
```

Soglia std calibrata sul 33° percentile dei dati storici (valore assoluto fisso: 0.0417).
ROI storico atteso: **+10.2%** su 393 partite.

---

## Analisi tendenze stagionali (11/05/2026)

Script: `notebooks/analisi_tendenze_stagionali.py`

### Idea
Usare la prima metà della stagione per classificare le squadre (`high_win`, `high_draw`, `high_loss`) e verificare se quella tendenza è predittiva nella seconda metà.

### Persistenza delle tendenze

| Tendenza | Conferma nella seconda metà |
|---|---|
| high_win | **65.2%** ✅ |
| high_loss | 46.2% |
| high_draw | 32.4% ❌ (troppo volatile) |

### Risultato: il segnale stagionale non aggiunge edge

| Strategia | Partite | Win rate | ROI |
|---|---|---|---|
| Solo filtro base | 160 | 64.4% | +0.035 |
| Filtro base + high_win_away | 61 | 65.6% | +0.036 |

Il ROI è quasi identico. Il motivo: le quote già incorporano la forma della squadra.

**Conclusione: si usa solo il filtro base.**

---

## Stato implementazione (14/05/2026 — finale)

| Componente | Stato | Note |
|---|---|---|
| `src/training/preprocess.py` | ✅ | Preserva `date`, `home_team`, `away_team` |
| `src/training/train.py` | ✅ | Esclude le nuove colonne dalle feature |
| `src/prediction/predict.py` | ✅ | `build_features_from_odds()` + `predict_match()` con `value_bet: bool` |
| `src/analysis/team_tendencies.py` | ✅ | Modulo tendenze stagionali (non usato in produzione) |
| `src/db/storage.py` | ✅ | SQLite: salva predizioni, risultati reali, calcola ROI |
| `src/db/update_results.py` | ✅ | Match automatico predizioni → risultati dai CSV |
| `src/ui/app.py` | ✅ | Value Bet, Storico ROI, Kelly criterion toggle |
| `src/scraper/odds_live.py` | ✅ | Quote live funzionanti con API key reale |
| `notebooks/analisi_value_betting.py` | ✅ | Calibrazione + backtest + stabilità ROI per stagione |
| `notebooks/analisi_tendenze_stagionali.py` | ✅ | Backtest segnale combinato (non usato in produzione) |

## TODO — Da fare

Nessun TODO aperto. Il sistema è completo e pronto per l'uso in produzione.

Prossimo passo operativo: dopo la giornata del 17/05/2026, scaricare i CSV aggiornati e cliccare "Aggiorna risultati" per verificare il ciclo completo.

---

## Analisi Strategia Mista (22/05/2026)

Vedi documento separato: `notebooks/analisi_strategia_mista.py` e sezione dedicata in `ComeNasce.md`.

In sintesi: il filtro value bet (prob_A > 0.45, std_A < 0.0417) rimane valido come segnale di lungo periodo, ma il ROI si è azzerato nelle ultime 3 stagioni (2223-2425). La nuova strategia mista 9-safe+1-jolly con monitor ROI stagionale è il complemento operativo: permette di intercettare automaticamente le stagioni in cui il mercato torna inefficiente.
