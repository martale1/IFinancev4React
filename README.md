# 📈 IFinance v4 React

> Piattaforma di **analisi tecnica** e **screening** dei mercati finanziari con backend Python/FastAPI e frontend React/TypeScript.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)

---

## 🗂 Indice

- [Panoramica](#-panoramica)
- [Architettura](#-architettura)
- [Funzionalità principali](#-funzionalità-principali)
- [Stack tecnologico](#-stack-tecnologico)
- [Struttura del progetto](#-struttura-del-progetto)
- [Setup e avvio](#-setup-e-avvio)
- [Variabili d'ambiente](#-variabili-dambiente)
- [Mercati supportati](#-mercati-supportati)
- [API Reference](#-api-reference)
- [Motore di Analisi Tecnica (TechnicalAnalyzer)](#-motore-di-analisi-tecnica-technicalanalyzer)
- [Opportunity Radar](#-opportunity-radar)
- [Multi-Pattern Lab](#-multi-pattern-lab)
- [Sistema di Alert](#-sistema-di-alert)
- [AI Integration](#-ai-integration)

---

## 🔭 Panoramica

IFinance v4 React è un'applicazione **full-stack** pensata per il trader quantitativo che vuole:

- **Monitorare** watchlist di titoli su più mercati (FTSE MIB, DAX, US, ETC/ETF, liste personalizzate)
- **Scansionare** pattern tecnici in real-time su centinaia di ticker
- **Fare backtest** istantanei con VectorBT direttamente dalla UI
- **Ricevere alert** automatici via Telegram quando un titolo soddisfa regole configurabili
- **Analizzare** grafici con un AI Analyst (OpenAI) integrato

L'architettura è **completamente locale**: nessun dato viene inviato a servizi cloud se non le chiamate AI esplicite.

---

## 🏗 Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    BROWSER (localhost:5173)              │
│                                                         │
│  React 18 + TypeScript + Vite                           │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐  │
│  │Watchlist │ │ Scanner │ │  Alerts  │ │  AI Chat   │  │
│  │  Cards   │ │   Lab   │ │  Panel   │ │   Panel    │  │
│  └──────────┘ └─────────┘ └──────────┘ └────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / SSE
                        ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND (localhost:8011)                   │
│                                                         │
│  FastAPI + Uvicorn                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Watchlist   │  │   Scanner    │  │   Alerts     │  │
│  │   Service    │  │   Service    │  │   Service    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
│  ┌──────▼─────────────────▼─────────────────▼───────┐  │
│  │            TechnicalAnalyzer (core engine)        │  │
│  │   yfinance · pandas · ta-lib · VectorBT           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  AI Service  │  │  Telegram    │                     │
│  │  (OpenAI)    │  │  Messaging   │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  analyses/ dir  │
              │  (JSON cache)   │
              └─────────────────┘
```

---

## ✨ Funzionalità principali

### 📊 Watchlist & Screening
- Visualizzazione tabellare di tutti i titoli per mercato con score tecnico
- Filtri per tab: **All**, **Alerts**, **AI Chat**, **Early Trend**, **Expansion**, **Buy**, **Pullback**, **Migliori (1D/5D)**
- Ricerca live per ticker/nome, filtro per volume minimo
- Paginazione lato server
- **Rigenerazione analisi** on-demand con un click

### 🎯 Opportunity Radar
- Classifica unica **Top 20** dei titoli più interessanti, deduplicata tra i mercati
- Profili **Bilanciato**, **Reversal**, **Trend iniziale**, **Momentum** e **Recovery Setup**
- Finestra di anzianità configurabile a 5, 10 o 20 sedute
- Score trasparente basato sui segnali S2–S8, freschezza, forza del trend e liquidità relativa
- Evidenza separata dei motivi positivi e dei principali rischi tecnici

### 🔬 Multi-Pattern Lab
Scanner di pattern tecnici con simulazione VectorBT istantanea:

| Pattern | Descrizione |
|---------|-------------|
| **S2** – willR+Stoch | Williams %R + Stocastico in zona oversold |
| **S3** – MACD Cross | Incrocio MACD rialzista confermato |
| **S4** – EMA+RSI+Vol | EMA9 sopra EMA21 + RSI momentum + volume |
| **Comb. S2&S3** | Combinazione S2 e S3 |
| **S5 – RSI Oversold** | RSI < 30 con incrocio stocastico rialzista |
| **S6 – Golden Cross** | EMA30 incrocia sopra EMA50 nella seduta, con ADX > 25 |
| **S7 – Alligator Bull** | Ingresso in stato Close > SAR e Alligator Uptrend |
| **S8 – Volume Breakout** | Candela rialzista con volume > 1.5x MA20 |
| *Pattern personalizzati* | Definibili dall'utente via YAML |

Per ogni scansione si ottengono:
- Lista titoli con segnale attivo
- Backtest storico (win rate, Sharpe, max drawdown, avg return)
- Grafico equity curve
- Commentary AI opzionale

### 🔔 Sistema di Alert
- Regole configurabili per ogni mercato (YAML-based)
- Motore di alert eseguibile on-demand o schedulato
- Notifiche via **Telegram** (multi-canale)
- Storico degli alert con toggle attiva/disattiva per ogni regola

### 🤖 AI Integration
- **AI Chat Panel**: conversazione libera con contesto dei dati di mercato correnti
- **AI Analyst**: analisi del grafico tecnico del singolo ticker (visione del chart PNG + commento)
- Basato su **OpenAI Agents SDK**

### 📋 Gestione Liste
- Creazione e gestione di watchlist personalizzate
- Aggiunta/rimozione ticker da UI
- Supporto mercati: MIB30, ETC, ETF, Preferite, US_Others, DAX + custom

### 📤 Export
- Export PDF dei titoli in segnale **BUY** per mercato

---

## 🛠 Stack tecnologico

### Backend
| Libreria | Versione | Scopo |
|----------|----------|-------|
| `fastapi` | ≥ 0.115 | Framework REST API |
| `uvicorn[standard]` | ≥ 0.30 | Server ASGI con hot-reload |
| `pandas` | ≥ 2.0 | Manipolazione dati / DataFrame |
| `yfinance` | ≥ 0.2.50 | Download dati OHLCV da Yahoo Finance |
| `matplotlib` | ≥ 3.7 | Generazione grafici tecnici (PNG) |
| `openpyxl` | ≥ 3.1 | Export Excel |
| `pyyaml` | ≥ 6.0 | Configurazione pattern personalizzati |
| `openai-agents` | ≥ 0.2 | AI Analyst e chat |
| `telepot` | ≥ 12.7 | Notifiche Telegram |
| `vectorbt` | — | Backtest (dipendenza implicita) |

### Frontend
| Libreria | Versione | Scopo |
|----------|----------|-------|
| `react` | 18.3 | UI framework |
| `react-dom` | 18.3 | Rendering DOM |
| `typescript` | 5.6 | Type safety |
| `vite` | 5.4 | Build tool / dev server |
| `@tanstack/react-query` | 5.59 | Data fetching & caching |

---

## 📁 Struttura del progetto

```
IFinancev4React/
│
├── backend/                    # Server FastAPI
│   ├── app/
│   │   ├── main.py             # Entry point + tutti gli endpoint REST
│   │   ├── config.py           # Configurazione paths e mercati
│   │   ├── schemas.py          # Modelli Pydantic request/response
│   │   ├── ai/
│   │   │   └── service.py      # Integrazione OpenAI Agents
│   │   └── services/
│   │       ├── watchlist_service.py      # Caricamento e filtraggio watchlist
│   │       ├── scanner_service.py        # Pattern scanner + VectorBT backtest
│   │       ├── alerts_service.py         # Motore di alert
│   │       ├── chart_service.py          # Generazione grafici PNG
│   │       ├── export_service.py         # Export PDF
│   │       ├── custom_watchlists_service.py
│   │       └── access_log_service.py
│   └── requirements.txt
│
├── frontend/                   # App React
│   ├── src/
│   │   ├── components/
│   │   │   ├── WatchlistCard.tsx         # Card titolo con tutti gli indicatori
│   │   │   ├── MultiPatternLabPanel.tsx  # Scanner pattern + backtest UI
│   │   │   ├── AlertsPanel.tsx           # Gestione alert
│   │   │   ├── AiChatPanel.tsx           # Chat AI
│   │   │   ├── AiTickerModal.tsx         # Analisi AI singolo ticker
│   │   │   ├── ChartModal.tsx            # Visualizzatore grafico tecnico
│   │   │   ├── ListManagerPanel.tsx      # Gestione liste personalizzate
│   │   │   ├── PatternManagerPanel.tsx   # Gestione pattern YAML
│   │   │   └── RuleGuide.tsx             # Guida regole/segnali
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
│
├── TechnicalAnalyzer.py        # Core engine di analisi tecnica
├── ChartManager.py             # Generazione grafici matplotlib
├── AlertEngine.py              # Motore di alert standalone
├── analyses/                   # Cache JSON delle analisi per mercato
├── custom_patterns.yaml        # Pattern personalizzati utente
├── .env                        # Variabili d'ambiente (non in git)
└── .env.example                # Template variabili d'ambiente
```

---

## 🚀 Setup e avvio

### Prerequisiti
- **Anaconda** / Miniconda con environment `IFinanceTA`
- **Node.js** ≥ 18 + npm
- Python ≥ 3.11

### 1. Clona il repository
```bash
git clone https://github.com/martale1/IFinancev4React.git
cd IFinancev4React
```

### 2. Configura le variabili d'ambiente
```bash
cp .env.example .env
# Edita .env con le tue credenziali Telegram e OpenAI
```

### 3. Avvia il Backend
```bash
cd backend

# Con conda (Windows)
C:\Users\<utente>\anaconda3\Scripts\conda.exe run -n IFinanceTA uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload

# Con conda (Linux/Mac)
conda activate IFinanceTA
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload
```

Il backend sarà disponibile su **http://localhost:8011**  
Documentazione interattiva Swagger: **http://localhost:8011/docs**

### 4. Avvia il Frontend
```bash
cd frontend
npm install       # Solo la prima volta
npm run dev
```

Il frontend sarà disponibile su **http://localhost:5173**

### Installazione su Raspberry Pi (ARM64)

Questa procedura richiede un Raspberry con sistema operativo a 64 bit. Verifica che `uname -m` restituisca `aarch64`. Su Raspberry Pi 3 l'analisi completa, soprattutto della lista ETF, può richiedere molto tempo; è consigliato usare `tmux` e disporre di swap sufficiente.

```bash
# Pacchetti di sistema
sudo apt update
sudo apt install -y git curl build-essential tmux nodejs npm

# Miniforge ARM64
cd ~
curl -L -o Miniforge3.sh \
  https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3.sh -b -p "$HOME/miniforge3"
source "$HOME/miniforge3/bin/activate"
conda init bash
source ~/.bashrc

# Repository e branch Raspberry
git clone --branch sicilia2026 --single-branch \
  https://github.com/martale1/IFinancev4React.git
cd IFinancev4React

# Ambiente Python e dipendenze native ARM64
conda create -n IFinanceTA python=3.11 -y
conda activate IFinanceTA
conda install -c conda-forge -y numpy pandas scipy numba ta-lib pyarrow
pip install -r backend/requirements.txt
pip install vectorbt

# Configurazione locale (non committare .env)
cp .env.example .env
nano .env

# Dipendenze frontend
cd frontend
npm install
npm run build
cd ..
```

Verifica l'ambiente prima di generare i dati:

```bash
python -c "import talib, vectorbt, pandas, yfinance; print('Python OK')"
node --version  # deve essere >= 18
```

Le liste ticker di input in `validTickersXLS/` sono distribuite tramite Git. Gli Excel di analisi in `analyses/` sono invece generati localmente. Alla prima installazione avvia quindi `main.py` dalla radice del progetto:

```bash
tmux new -s ifinance-main
conda activate IFinanceTA
python main.py
```

Per lasciare il processo attivo e uscire da `tmux`, premi `Ctrl+B` e poi `D`. Per rientrare usa `tmux attach -t ifinance-main`.

Avvia poi backend e frontend in due terminali separati:

```bash
# Backend
cd ~/IFinancev4React/backend
conda run -n IFinanceTA python -m uvicorn app.main:app --host 0.0.0.0 --port 8011

# Frontend
cd ~/IFinancev4React/frontend
npm run dev -- --host 0.0.0.0
```

Da un altro dispositivo della stessa rete apri `http://<IP_RASPBERRY>:5173`. Ricava l'indirizzo con `hostname -I`. Non esporre direttamente le porte 5173 e 8011 su Internet.

In alternativa, lo script Raspberry avvia in background il backend e serve direttamente la build React sulla porta 8011:

```bash
cd ~/IFinancev4React
./start_raspberry.sh
```

Sul Raspberry Pi 3 il primo caricamento può richiedere fino a due minuti; lo script attende che l'API risponda prima di stampare l'indirizzo della pagina.

Per controllare il log o arrestare l'applicazione:

```bash
tail -f logs/ifinance.log
./stop_raspberry.sh
```

---

## 🔧 Variabili d'ambiente

Copia `.env.example` in `.env` e configura:

| Variabile | Descrizione | Obbligatoria |
|-----------|-------------|:------------:|
| `TELEGRAM_RECEIVER_ID` | Chat ID Telegram destinatario alert | ⚠️ Per alert |
| `TELEGRAM_BOT_TOKEN_CH0..5` | Token bot Telegram (uno per canale) | ⚠️ Per alert |
| `TELEGRAM_BOT_TOKEN_DEFAULT` | Token fallback per canali sconosciuti | No |
| `ANALYSES_DIR` | Path directory cache analisi JSON | No (default: `analyses/`) |
| `LOGS_DIR` | Path directory log | No (default: `logs/`) |
| `FRONTEND_DIST_DIR` | Path build frontend (per produzione) | No |
| `CORS_ORIGINS` | Origini CORS aggiuntive (comma-separated) | No |
| `OPENAI_API_KEY` | API Key OpenAI per le funzioni AI | ⚠️ Per AI |

---

## 🌍 Mercati supportati

| Mercato | Descrizione |
|---------|-------------|
| `MIB30` | FTSE MIB – principali titoli italiani |
| `DAX` | DAX 40 – mercato tedesco |
| `ETC` | Exchange Traded Commodities |
| `ETF` | Exchange Traded Funds |
| `Preferite` | Watchlist personale dell'utente |
| `US_Others` | Titoli USA extra-indice |
| *Custom* | Liste create dall'utente dalla UI |

---

## 📡 API Reference

### Watchlist
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/markets` | Lista mercati disponibili |
| `GET` | `/api/watchlist` | Dati watchlist con filtri e paginazione |
| `GET` | `/api/watchlist/focus` | Titoli in focus (segnale forte) |
| `POST` | `/api/watchlist/regenerate` | Rigenera analisi per un mercato |

### Grafici & Export
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/charts/{ticker}` | Grafico tecnico PNG del ticker |
| `POST` | `/api/export/buy-pdf` | Export PDF segnali BUY |

### Scanner
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/scanner/scan` | Scansione pattern (batch) |
| `GET` | `/api/scanner/scan-stream` | Scansione in streaming SSE (real-time) |
| `GET` | `/api/scanner/backtest` | Backtest VectorBT su pattern |
| `GET` | `/api/scanner/backtest/chart` | Equity curve PNG del backtest |
| `GET` | `/api/scanner/custom-patterns` | Lista pattern personalizzati |
| `POST` | `/api/scanner/custom-patterns/save` | Salva pattern personalizzato |

### Alert
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/alerts/{market}` | Regole di alert per mercato |
| `POST` | `/api/alerts/{market}/upsert` | Crea/aggiorna regola alert |
| `POST` | `/api/alerts/run` | Esegui motore alert manualmente |

### Watchlist personalizzate
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/custom-watchlists` | Lista watchlist custom |
| `POST` | `/api/custom-watchlists` | Crea nuova watchlist |
| `POST` | `/api/custom-watchlists/add-item` | Aggiungi ticker |
| `POST` | `/api/custom-watchlists/remove-item` | Rimuovi ticker |

### Ticker Lists (gestione liste per mercato)
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/api/ticker-lists/{market}` | Lista ticker del mercato |
| `POST` | `/api/ticker-lists/{market}/add` | Aggiungi ticker al mercato |
| `POST` | `/api/ticker-lists/{market}/remove` | Rimuovi ticker dal mercato |

### AI
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `POST` | `/api/ai/chat` | Chat AI con contesto di mercato |
| `POST` | `/api/ai/analyze-chart` | Analisi AI del grafico tecnico |

---

## 🧠 Motore di Analisi Tecnica (TechnicalAnalyzer)

Il cuore del sistema è la classe `TechnicalAnalyzer` in `TechnicalAnalyzer.py`.

### Utilizzo base
```python
from TechnicalAnalyzer import TechnicalAnalyzer

ta = TechnicalAnalyzer("RACE.MI", period="2y")
ta.calculate_TA_Indicators("MACD,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV")
```

### Indicatori disponibili
| Indicatore | Colonne prodotte |
|-----------|-----------------|
| `MACD` | `MACD`, `MACD_Signal`, `MACD_Hist`, `MACDH_Trend`, `MCS`, `MCS_Conf` |
| `RSI` | `RSI`, `RSI_Trend`, `RSI_Trend_Days` |
| `STOCH` | `Stoch_K`, `Stoch_D`, `SK_Trend`, `SK_Trend_Days` |
| `WILLR` | `Williams_R`, `WILLR_Trend`, `WILLR_Overbought`, `WILLR_Oversold` |
| `SAR` | `SAR`, `SAR_Above_Price` |
| `ALLIGATOR` | `Alligator_Jaw`, `Alligator_Teeth`, `Alligator_Lips`, `Signal6` |
| `EMA_30/50` | `EMA_30`, `EMA_50` |
| `PCTV` | `PCTV_1D`, `PCTV_5D`, `PCTV_10D`, `PCTV_30D`, `PCTV_180D` |

### Scoring e segnali
```python
# Calcola TECH_SCORE (0-100)
ta.calculate_technical_score(weights=custom_weights)

# Aggiunge categoria di trading
ta.add_category()  # → Category, EntryTrigger, StopHint, Notes
```

### Parametri chiave per il segnale MACD
```python
ta.build_macd_signal(
    min_streak=7,           # Giorni minimi MACD > 0 per "in trend"
    conf_min=0.30,          # Soglia minima MCS_Conf
    pct1d_range=(-1.5, 2.0), # Range variazione % giornaliera
    require_signal6_up=True, # Richiede Alligator in uptrend
    rsi_min=50.0,           # RSI minimo per ingresso
    rsi_ob_hard=78.0,       # RSI overbought hard (blocca ingresso base)
    use_breakout=True,      # Abilita ingresso alternativo su breakout
    breakout_lookback=5,    # Lookback barre per massimo breakout
)
```

---

## 🎯 Opportunity Radar

Il tab **Opportunity Radar** riduce l'universo analizzato a una Top 20 ordinata per qualità del setup. Usa i dati già calcolati da `main.py` negli Excel di `analyses/`, quindi il cambio di mercato, profilo o finestra non effettua nuovi download.

### Mercati, finestra e dati mostrati

- mercati selezionabili: **MIB30** (predefinito), ETF, ETC, DAX, Preferite oppure Tutti i mercati;
- anzianità massima del segnale: 5, 10 o 20 sedute;
- deduplicazione del ticker quando compare in più liste;
- prezzo, variazioni 1D/5D, RSI, ADX, ATR, volume e controvalore;
- motivi positivi e rischi che hanno contribuito al risultato.

La freschezza riduce progressivamente il contributo di ciascun pattern: un evento di oggi pesa più dello stesso evento avvenuto diversi giorni fa. Un ticker viene escluso quando non possiede segnali compatibili con il profilo nella finestra selezionata.

### Profili disponibili

| Profilo | Scopo | Pesi principali |
|---|---|---|
| **Bilanciato** | Setup con più conferme senza privilegiare un solo stile | S2 10, S3 12, S4 12, S5 10, S6 14, S7 12, S8 10 |
| **Reversal** | Ripartenze da condizioni depresse | S2 34, S5 38, S3 8 |
| **Trend iniziale** | Individuazione dell'avvio di un trend | S2 6, S3 22, S6 28, S7 24 |
| **Momentum** | Accelerazione accompagnata da prezzo e volume | S3 10, S4 34, S7 8, S8 30 |
| **Recovery Setup** | Titoli molto penalizzati che mostrano una possibile inversione | S2 24, S3 18, S5 22, S7 10, S8 12 |

Il punteggio combina:

- segnali S2–S8, con pesi diversi per il profilo selezionato;
- anzianità del segnale nella finestra scelta;
- qualità tecnica (ADX/DI, SAR, SMA200 e score tecnico);
- liquidità relativa del titolo nel proprio insieme di confronto;
- penalità esplicite per RSI elevato, volatilità ATR e accelerazioni a 5 giorni eccessive.

Inoltre ADX, DI+, SAR e SMA200 aggiungono o sottraggono qualità; la liquidità è valutata relativamente agli altri candidati della stessa scansione. Lo score è un ordinamento quantitativo, non una probabilità di guadagno.

### Recovery Setup: regole di ammissione

Recovery cerca un'inversione in corso, non semplicemente un titolo che ha perso molto. Un candidato deve rispettare tutte queste condizioni:

1. ribasso di almeno `-6%` a 30 giorni oppure `-15%` a 180 giorni;
2. presenza recente di un segnale diretto **S2 Reversal** o **S5 RSI Oversold**;
3. variazione giornaliera superiore a `-3%` e variazione a 5 giorni superiore a `-7%`;
4. assenza della combinazione nuovamente ribassista: prezzo sotto SAR, DI- sopra DI+, seduta negativa e Stochastic K non superiore a D.

In questo modo un segnale S2 ormai fallito non rimane tra i possibili recuperi.

### Tentativo e ripartenza confermata

- **Tentativo di recupero**: S2/S5 è presente, ma mancano ancora conferme sufficienti.
- **Ripartenza confermata**: oltre a S2/S5 esiste almeno uno tra S3, S7 o S8, il prezzo è sopra SAR e DI+ è sopra DI-.

La dicitura **Ripartenza confermata** riguarda gli indicatori già attivi. Non significa che il trigger operativo di prezzo sia già stato superato.

### Piano tecnico Recovery

Per ogni candidato vengono calcolati livelli sperimentali:

```text
buffer = max(ATR × 0,05; prezzo × 0,001)
trigger = max(chiusura, massimo ultima candela) + buffer
invalidazione = min(minimo ultima candela, SAR) - max(ATR × 0,20; prezzo × 0,002)
rischio % = (trigger - invalidazione) / trigger × 100
target 2R = trigger + 2 × (trigger - invalidazione)
```

- **Trigger ingresso sopra** (nell'interfaccia: “Conferma sopra”): soglia oltre la quale il prezzo conferma anche il breakout della candela corrente.
- **Distanza**: rialzo percentuale necessario dal prezzo corrente al trigger.
- **Invalidazione sotto**: livello oltre il quale il setup tecnico non è più valido.
- **Rischio tecnico**: ampiezza percentuale tra trigger e invalidazione; oltre l'8% viene segnalato come rischio ampio.
- **Obiettivo teorico 2R**: riferimento matematico pari a due volte il rischio assunto, non previsione del prezzo futuro.

Se il titolo è già salito almeno del 12% in cinque giorni, viene mostrato **Ingresso esteso: attendere pullback**. Un semplice superamento intraday del trigger può essere un falso breakout: il livello deve essere sempre controllato sul grafico insieme ai volumi.

### Alert automatico sulla conferma

Il pulsante **Crea alert sulla conferma** salva nel mercato sorgente una regola attiva:

```text
Close >= trigger Recovery
```

La regola invia al massimo una notifica al giorno e include nel messaggio trigger, invalidazione, RSI, ADX e volume. L'identificativo `RECOVERY_CONFIRM_<TICKER>` impedisce duplicati: un nuovo click aggiorna il livello già salvato.

Aprendo il grafico da una card Recovery, il trigger viene riportato nel pannello prezzo come linea orizzontale magenta tratteggiata **CONFERMA RECOVERY**, con lo stesso valore mostrato nel piano tecnico. I grafici aperti dalle altre sezioni non mostrano questa linea.

La classifica è uno strumento di screening e non costituisce consulenza finanziaria: il pulsante **Apri grafico** consente di verificare ogni candidato prima di qualsiasi decisione.

### API

```http
GET /api/opportunities?market=ALL&mode=balanced&limit=20&window=5
```

`market` accetta `ALL` oppure un mercato disponibile; `mode` accetta `balanced`, `reversal`, `early_trend`, `momentum` o `recovery`; `window` accetta da 1 a 30 sedute e `limit` da 5 a 100 risultati.

---

## 🔬 Multi-Pattern Lab

Il **Multi-Pattern Lab** è il modulo di screening avanzato. Permette di:

1. **Selezionare un pattern** tra quelli predefiniti o personalizzati
2. **Configurare** filtri (mercato, data, filtri tecnici)
3. **Avviare la scansione** — il backend itera su tutti i ticker del mercato selezionato
4. **Visualizzare i risultati** con i titoli che soddisfano il pattern
5. **Avviare il backtest VectorBT** su ogni titolo per validare la strategia storicamente

### Scansione rapida da Excel

Durante l'esecuzione, `main.py` calcola S2–S8 sull'intera serie storica di ogni ticker e salva nell'Excel di mercato le colonne:

- `Pattern_S2_Days_Ago` … `Pattern_S8_Days_Ago`: numero di sedute trascorse dall'ultimo segnale (`999` se assente)
- `Pattern_S2_Match` … `Pattern_S8_Match`: presenza del segnale sulla singola riga storica
- `Pattern_Combined_Days_Ago`: ultimo segnale congiunto S2 e S3
- `SAR_Filter_Ok` e `SMA200_Filter_Ok`: filtri tecnici pre-calcolati

I file vengono scritti in `analyses/<MERCATO>_TA_Analyses.xlsx`. Il backend usa queste colonne per S2–S8, **Comb. S2&S3** e **Qualsiasi S2/S3**, evitando nuovi download da Yahoo Finance durante la scansione. Se il file non esiste o proviene da una versione precedente e non contiene le colonne richieste, viene usata automaticamente la scansione realtime.

`main.py` esegue invece sempre un nuovo download da Yahoo Finance per ogni ticker (`USE_CACHE = False`, `CACHE_HOURS = 0`). I file parquet eventualmente presenti nella cartella `cache/` non vengono letti né aggiornati durante la generazione degli Excel, così la data di aggiornamento non può riferirsi a dati storici riutilizzati.

Le voci YAML `RSI Oversold`, `Golden Cross`, `Alligator Bull` e `Volume Breakout` sono mappate rispettivamente su S5, S6, S7 e S8 e sfruttano lo stesso percorso rapido.

### Pattern personalizzati (YAML)
Definisci i tuoi pattern in `custom_patterns.yaml`:
```yaml
patterns:
  - id: "my_pattern"
    label: "Il Mio Pattern"
    description: "Descrizione del segnale"
    conditions:
      - field: "RSI"
        op: "<"
        value: 35
      - field: "MACD_Hist"
        op: ">"
        value: 0
```

---

## 🔔 Sistema di Alert

Il sistema di alert consente di monitorare automaticamente le condizioni di mercato.

### Configurazione regole
Le regole sono gestibili dalla UI nel tab **Alerts** oppure direttamente via API:

```json
{
  "ticker": "ENI.MI",
  "market": "MIB30",
  "condition": "RSI < 35 AND MACD_Hist > 0",
  "message": "ENI oversold con MACD in recupero",
  "enabled": true
}
```

### Invio notifiche
Le notifiche vengono inviate su Telegram configurando i token nel file `.env`.
Il motore può essere eseguito:
- **Manualmente** dalla UI (pulsante "Esegui Alert")
- **Programmaticamente** via `POST /api/alerts/run`
- **Schedulato** con un task esterno (cron, Task Scheduler Windows)

---

## 🤝 Contribuire

Il progetto è in sviluppo attivo. Il branch principale di sviluppo è `versione1`.

```bash
git checkout versione1
git pull origin versione1
# ... fai le tue modifiche ...
git add .
git commit -m "feat: descrizione della modifica"
git push origin versione1
```

---

## 📄 Licenza

Progetto privato — tutti i diritti riservati.
