# Guida d'uso — App Predictor (Serie A, Serie B, La Liga 2, Bundesliga 2)

Guida comune a tutte e 4 le app Streamlit. Spiega la API key, il pulsante "Carica quote"
e cosa fa ogni tab. Le app sono identiche: cambia solo il campionato.

## URL delle app online

| App | URL |
|---|---|
| Serie A | https://seriea-predictor-app.streamlit.app/ |
| Serie B | (da deployare — `serieb-predictor` su share.streamlit.io) |
| La Liga 2 | (da deployare — `laliga2-predictor`) |
| Bundesliga 2 | (da deployare — `bundesliga2-predictor`) |

---

## 1) La ODDS_API_KEY (quote live)

Le quote reali arrivano da **The Odds API** (https://the-odds-api.com). Il piano gratuito
dà **500 richieste/mese**. La chiave è condivisa tra le 4 app; una cache di 6 ore limita il consumo.

### Dove sta la chiave
- **In locale**: nel file `.env` di ogni predictor (`ODDS_API_KEY=...`). NON è su GitHub (ignorata).
- **Online (Streamlit Cloud)**: nei **Secrets** dell'app (⋮ → Settings → Secrets), formato TOML:
  ```
  ODDS_API_KEY = "la_tua_chiave"
  ```
- Senza chiave, l'app funziona in **modalità mock** (toggle "Usa dati di esempio" nella sidebar).

### Come rigenerare / recuperare la chiave su the-odds-api.com
Il sito è in inglese. Passi:
1. Vai su **https://the-odds-api.com** e fai **Sign in** (in alto a destra) con l'account usato.
2. Arrivi alla **Dashboard** del tuo account.
3. Lì vedi:
   - **"Your API key"** → è la chiave attuale (puoi copiarla).
   - **"Requests used / remaining"** → quante delle 500 richieste mensili hai consumato.
4. Per **rigenerarla** (se vuoi invalidare la vecchia): cerca il pulsante **"Regenerate key"**
   o **"Reset key"** nella dashboard. Genera una chiave nuova e la vecchia smette di funzionare.
5. Dopo averla rigenerata, **aggiorna la chiave** in due posti:
   - i file `.env` locali dei 4 predictor
   - i **Secrets** delle 4 app su Streamlit Cloud

> Nota: se non ricevi la mail o non ricordi l'account, usa "Forgot password" sulla pagina di login.

---

## 2) Il pulsante "Carica quote"

Nella tab **Predizioni giornata**. Cliccandolo l'app:
1. chiama The Odds API e scarica le quote 1/X/2 delle **prossime partite** del campionato;
2. le mette in cache per 6 ore (una seconda chiamata entro 6h NON consuma una richiesta API);
3. passa le quote al modello, che produce le predizioni.

Se il toggle "Usa dati di esempio" è attivo, carica quote **finte** (per provare senza consumare l'API).
Se manca la chiave e il toggle è spento → errore "ODDS_API_KEY non configurata".

---

## 3) Cosa fa ogni TAB

### 🔮 Predizioni giornata
Il cuore dell'app. Premi **Carica quote** → per ogni partita in programma mostra:
- la **predizione** 1 / X / 2 (esito più probabile secondo il modello)
- le **probabilità** di Casa, Pareggio, Trasferta
- la **confidenza** e un flag **Value Bet** (scommessa con valore atteso favorevole)
- (se attivi Kelly nella sidebar) lo **stake** suggerito

Esporta anche un CSV delle predizioni. Le predizioni vengono salvate nel DB locale.

### ✏️ Inserimento manuale
Per analizzare **una singola partita** inserendo tu le quote a mano (1, X, 2 di Bet365),
senza passare dalle quote live. Scrivi le due squadre e le 3 quote, premi **Predici** e
ottieni predizione + probabilità. Utile per "cosa dice il modello se le quote fossero queste?".

### 🔄 Aggiorna dataset
Manutenzione del modello (NON i risultati). Due pulsanti:
- **Scarica nuovi dati storici** → riscarica i CSV da football-data.co.uk
- **Ri-addestra modello** → rigenera il dataset e riallena XGBoost sui dati aggiornati

Da usare a inizio/durante stagione per tenere il modello fresco. In locale; online ha senso solo
se poi ricommitti modello+dataset (vedi `docs/deploy_streamlit.md`).

### 📊 Storico
Le predizioni **già fatte** e il loro esito reale. Qui:
- il pulsante **Aggiorna risultati** cerca nei CSV storici l'esito vero delle partite predette
  e lo registra (ATTENZIONE: diverso da "Aggiorna dataset" — qui aggiorni i *risultati*, lì il *modello*)
- mostra **win rate** e **ROI reale** sulle value bet
- puoi inserire manualmente l'esito di una partita

> Su Streamlit Cloud il DB (SQLite) NON persiste tra i riavvii: lo storico ROI ha senso solo in locale.

### 🎯 Strategia Mista
La strategia operativa **9 safe + 1 jolly**:
- **SAFE**: partite dove il modello è molto sicuro (gap di probabilità ≥ 15%) → si punta sull'esito probabile
- **JOLLY**: 1 partita ad alta quota (≥ 5.0) → piccola puntata ad alto potenziale
- Premi **Calcola segnali giornata** per generarli dalle quote correnti
- Mostra il **ROI stagionale** e un alert **🔥 STAGIONE CALDA** quando il mercato è inefficiente
  (ROI ≥ 8% su almeno 20 scommesse) → è il momento in cui la strategia rende di più

---

## Riepilogo rapido

| Voglio... | Dove |
|---|---|
| Vedere le predizioni della prossima giornata | Tab Predizioni → Carica quote |
| Provare una partita con quote mie | Tab Inserimento manuale |
| Tenere aggiornato il modello | Tab Aggiorna dataset (in locale) |
| Registrare gli esiti reali e vedere il ROI | Tab Storico → Aggiorna risultati |
| Le scommesse consigliate (safe + jolly) | Tab Strategia Mista |
| Cambiare/controllare la API key | the-odds-api.com (dashboard) + Secrets/​.env |
