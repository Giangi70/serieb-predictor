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

## 1-bis) I due interruttori nella sidebar (Impostazioni)

Nella barra laterale a sinistra ci sono due toggle on/off. Sono **indipendenti** tra loro.

### 🔘 "Usa dati di esempio (no API key)"
Sceglie **da dove arrivano le quote** quando premi "Carica quote":
- **ON** → quote **finte** (mock): NON chiama The Odds API, NON consuma richieste, funziona senza chiave.
  Utile per **provare** l'app. (Se vedi quote strane/inventate, è questo toggle acceso.)
- **OFF** → quote **reali** scaricate da The Odds API.

Il valore iniziale è automatico: parte **ON se non c'è la chiave**, OFF se la chiave è presente.
Per l'uso reale tienilo **OFF**.

### 🔘 "Kelly criterion"
Riguarda **quanto scommettere** (lo stake), non la predizione:
- **OFF** → l'app indica solo *quali* sono le value bet, senza importi.
- **ON** → compare il campo **"Bankroll (€)"** (il tuo capitale, default 100) e per ogni value bet
  l'app calcola lo **stake consigliato** con la formula di Kelly.

Il **criterio di Kelly** è una formula che dice quale frazione del capitale puntare per far crescere
il bankroll in modo ottimale nel lungo periodo: più la scommessa ha valore atteso alto, più suggerisce
di puntare; se il vantaggio è piccolo, suggerisce poco. Serve a dimensionare le puntate razionalmente.

```
stake = ( p·b − (1−p) ) / b  ×  bankroll      (p = probabilità stimata, b = quota − 1)
```

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

## Flusso settimanale (come costruire lo storico e il ROI)

Il ciclo giornata per giornata è questo:

```
GIORNATA N — prima che si gioghi
  Tab "Predizioni giornata" → Carica quote
     → le predizioni vengono SALVATE AUTOMATICAMENTE nel DB
       (non devi fare altro: le ritrovi subito in tab "Storico" con Risultato vuoto)

DOPO che le partite si sono giocate (di solito la giornata dopo)
  Tab "Storico" → Aggiorna risultati
     → compila l'esito reale (H/D/A) delle partite che avevi predetto
     → solo ora il ROI e le statistiche si aggiornano
  (in alternativa puoi inserire l'esito a mano, sempre in tab Storico)
```

### Attenzione: NON è "Aggiorna dataset"
Due nomi simili, due cose diverse:
- **Storico → Aggiorna risultati** = registra gli ESITI REALI delle tue predizioni ← **questo serve per lo storico/ROI**
- **Aggiorna dataset** = riscarica i CSV e RI-ALLENA il modello ← manutenzione del modello, NON lo storico

### Chiarimento sul "servono ≥ 20 scommesse"
Quel 20 **non sono 20 giornate**: sono 20 **scommesse con esito registrato**. Una predizione
salvata ma senza risultato NON conta. Il contatore sale solo dopo "Aggiorna risultati".

### ⚠️ Lo storico persiste SOLO in locale
Su **Streamlit Cloud** il database SQLite **si azzera a ogni riavvio** dell'app (e il cloud
gratuito si riavvia spesso, dopo inattività o throttle). Quindi:
- **app online** → ottima per *consultare* le predizioni della giornata; lo storico NON si accumula
- **app in locale** (`./start.sh`) → qui il file `data/*.db` è permanente: è l'unico posto dove
  costruire davvero lo storico ROI settimana dopo settimana

Per avere lo storico persistente anche online servirebbe un database esterno (es. Postgres
gratuito) al posto di SQLite — sviluppo futuro, non ancora implementato.

---

## Riepilogo rapido

| Voglio... | Dove |
|---|---|
| Vedere le predizioni della prossima giornata | Tab Predizioni → Carica quote |
| Provare una partita con quote mie | Tab Inserimento manuale |
| Tenere aggiornato il modello | Tab Aggiorna dataset (in locale) |
| Registrare gli esiti reali e vedere il ROI | Tab Storico → Aggiorna risultati (in locale) |
| Le scommesse consigliate (safe + jolly) | Tab Strategia Mista |
| Usare quote vere (non finte) | Sidebar → "Usa dati di esempio" OFF |
| Farmi suggerire quanto puntare | Sidebar → "Kelly criterion" ON + Bankroll |
| Cambiare/controllare la API key | the-odds-api.com (dashboard) + Secrets/​.env |
