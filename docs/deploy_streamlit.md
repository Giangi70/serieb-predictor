# Deploy — UI online su Streamlit Community Cloud

Guida operativa per pubblicare la **UI del predictor** su un URL pubblico,
accessibile da qualsiasi browser (anche smartphone). Costo: **0 €/mese**.

Modello scelto: **Streamlit Community Cloud + repo GitHub + URL `*.streamlit.app`**.
Stesso spirito del deploy del Grifo su Cloudflare: *repo GitHub → la piattaforma builda →
URL pubblico → ogni push aggiorna*. La differenza è che Streamlit Cloud **esegue** l'app
Python (il Grifo era statico e bastava Cloudflare Pages).

---

## Perché modello e dati sono versionati

In locale `start.sh` scarica i CSV e addestra il modello al primo avvio. Su Streamlit Cloud
l'app parte da un **clone pulito del repo** e il filesystem è effimero: non si può dipendere
dal training al boot (lento e fragile). Quindi, per il deploy, nel repo **sono versionati**:

- `models/model.joblib` — il modello già addestrato (~1,4 MB)
- `data/processed/dataset.csv` — il dataset pronto (~0,4 MB)
- `data/raw/*.csv` — i CSV storici (servono alla tab "Aggiorna risultati")

Così l'app è autonoma: apri l'URL e funziona subito, senza attese.
(Questo è lo stesso principio del Grifo, dove `data/` è versionato ed è online al push.)

---

## Setup Streamlit Cloud (una tantum)

1. L'app è già su GitHub: `https://github.com/Giangi70/serieb-predictor`
2. Vai su **https://share.streamlit.io** e accedi con GitHub.
3. **Create app** → **Deploy a public app from GitHub**.
4. Compila:

   | Campo | Valore |
   |-------|--------|
   | Repository | `Giangi70/serieb-predictor` |
   | Branch | `main` |
   | Main file path | `src/ui/app.py` |

5. (Opzionale) **Advanced settings** → **Secrets**: se vuoi le quote live, incolla
   ```
   ODDS_API_KEY = "la_tua_chiave"
   ```
   Senza, l'app usa i dati mock (toggle "Usa dati di esempio" già attivo di default).

6. **Deploy**. In 1-2 minuti l'app è online su un URL tipo
   `https://serieb-predictor.streamlit.app`.

---

## Prerequisiti critici (lezioni dal deploy reale del 02/11/2026)

Due cose, se mancano, fanno fallire il deploy:

### 1. Repo pubblici (predictor + betting-core)
Streamlit Cloud (tier gratuito, opzione "public app") clona i repo **in anonimo**.
Sia il predictor **sia `betting-core`** (dipendenza in `requirements.txt`) devono essere
**pubblici**, altrimenti il clone fallisce con:
`fatal: could not read Username for 'https://github.com'`.

### 2. Python 3.11 obbligatorio (`.python-version`)
Di default Streamlit Cloud usa **Python 3.14**, per cui `scikit-learn==1.4.2` / `numpy==1.26.4`
**non hanno wheel precompilati** → il build prova a compilarli dai sorgenti e fallisce con:
`No solution found ... numpy==2.0.0rc1 ... unsatisfiable`.

Soluzione: il file **`.python-version`** (contenuto: `3.11`) nella root del repo. `uv`
(l'installer di Streamlit) lo rispetta. **NB: `runtime.txt` viene ignorato** da Streamlit/uv.
In alternativa/aggiunta: pannello app → Settings → Python version → 3.11.
Python 3.11 ha i wheel per tutte le versioni pinnate e coincide con l'ambiente di training.

### 3. ODDS_API_KEY nei Secrets, NON nel .env
Il file `.env` è locale e NON arriva sul cloud (è nel `.gitignore`). Se l'app dice
`ODDS_API_KEY non configurata nel file .env`, la chiave va messa nei **Secrets** di Streamlit
(⋮ → Settings → Secrets), in formato TOML:
```
ODDS_API_KEY = "la_tua_chiave"
```
Senza chiave l'app funziona comunque in modalità mock (toggle "Usa dati di esempio").

### Nota: throttling
Dopo molti rebuild ravvicinati, Streamlit può applicare un **throttle** (CPU ridotta,
l'app resta online). Non è un errore: scade da solo dopo qualche ora. Evitare reboot ripetuti.

---

## Flusso a regime

Dopo il setup, ogni push aggiorna l'app automaticamente:

```
modifichi → git push → Streamlit Cloud ribuilda → online in ~1-2 min
```

Se riaddestri il modello in locale, ricommitta `models/model.joblib` e
`data/processed/dataset.csv` prima del push.

---

## Limiti noti (importanti)

| Limite | Dettaglio | Impatto |
|--------|-----------|---------|
| **SQLite non persiste** | Il DB (`*.db`) è escluso dal repo e il filesystem cloud è effimero | Puoi *consultare* predizioni e segnali; lo **storico ROI** e il salvataggio risultati hanno senso solo in locale (o con un DB esterno, passo futuro) |
| **App "dorme"** | Dopo inattività l'app va in sleep | Il **primo accesso** dopo una pausa impiega ~30 sec a risvegliarsi, poi è veloce |
| **Quote live** | Richiedono `ODDS_API_KEY` nei Secrets | Senza, si usa il mock (va bene per guardare il funzionamento) |

Nessuno di questi impedisce l'obiettivo "mi collego e guardo le predizioni".

---

## Verifica pre-deploy (locale)

Simula l'ambiente cloud eseguendo dalla root del repo:

```bash
cd /home/egiabot/PROJECT/serieb-predictor
source /home/egiabot/venvs/serieb-predictor/bin/activate
streamlit run src/ui/app.py
# → http://localhost:8501  (deve partire senza "modello non trovato")
```

Se parte in locale da un clone con modello+dataset versionati, funzionerà identico online.
