# Run React MVP (Backend + Frontend)

## Prerequisites
- Python 3.10+ available as `python3` or your virtualenv interpreter.
- Node.js 18+ and npm.

## 1) Configure environment
1. Create `.env` from `.env.example`.
2. Fill at least:
   - `TELEGRAM_RECEIVER_ID`
   - `TELEGRAM_BOT_TOKEN_CH5` (or other channels you use)
   - `ANALYSES_DIR`, `LOGS_DIR` if your paths are different.

## 2) Local development
Start FastAPI on a private local port. The Vite dev server proxies `/api` to it, so the browser always calls the same public origin (`:5173`).

Use the conda environment used by this project:

From project root:

```powershell
conda activate openaiAgent
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Check health:
- [http://127.0.0.1:8010/api/health](http://127.0.0.1:8010/api/health)
- [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:
- [http://127.0.0.1:5173](http://127.0.0.1:5173)

## 3) Server deployment on one public port
Build React once, then let FastAPI serve both the app and `/api` from the same origin:

```powershell
cd frontend
npm install
npm run build

cd ..\backend
conda activate openaiAgent
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5173
```

Open:
- [http://theoiziruam.ddns.net:5173](http://theoiziruam.ddns.net:5173)

Only port `5173` needs to be reachable from outside. The frontend uses relative `/api` URLs, so it no longer calls private LAN addresses or a separate public backend port.

## Notes
- Analysis files are loaded from `analyses/` relative to the copied project root by default. If you set `ANALYSES_DIR` in `.env`, relative values such as `analyses` are still resolved from the project root.
- Backend reads the same `analyses/*.xlsx`, `alert_rules_*.yaml`, `alert_state_*.json` files used by Streamlit.
- `ALERTS` tab in React can trigger `AlertEngine` with channel 5 by default.
- Chart modal consumes `/api/charts/{ticker}` and renders server-side matplotlib output.
