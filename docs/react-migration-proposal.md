# React Migration Proposal - webAppv4.14

## Goal
Rebuild `webAppv4.14.py` as a React web app with improved UX, while preserving current functional behavior.

## Recommended Architecture
- Frontend: React + Vite + TypeScript + Tailwind + TanStack Query.
- Backend: FastAPI (Python), reusing current business logic modules.
- Data layer (phase 1): keep existing Excel/YAML/JSON files.
- Data layer (phase 2): optional migration to SQLite/Postgres.

## Main Functional Areas to Port
- Market picker and URL focus mode (`?market=...&ticker=...`).
- Watchlist cards with:
  - Action/Market Phase pills
  - Pullback/Stop/Profit Protect levels
  - Technical details checklist
  - Chart open/close
- Tabs:
  - BUY, AZIONI (tutte), PULLBACK, BREAKOUT, SELL
  - Migliori/Peggiori (1D/5D)
  - ALERTS tab with full rule management
- Alert system:
  - Per-ticker rules (YAML)
  - Market-wide rules
  - State counters (`Fired_Today`, `Fired_Total`, `Last_Alert`)
  - Run engine now (Telegram dispatch)
- BUY PDF export with multi-page charts.
- Access log (`iduser`, clean URL, query params).

## Backend API Contract (MVP)
- `GET /api/markets`
- `GET /api/watchlist?market=...&min_volume=...&tab=...&page=...&page_size=...`
- `GET /api/watchlist/focus?market=...&ticker=...`
- `GET /api/charts/{ticker}?bars=...&chart_type=candlestick|line`
- `POST /api/export/buy-pdf`
- `GET /api/alerts/{market}`
- `PUT /api/alerts/{market}`
- `POST /api/alerts/{market}/run`
- `GET /api/access-log/health`

## Frontend UX Improvements
- Sticky top bar with market selector + quick search.
- Collapsible filter panel (desktop sidebar / mobile drawer).
- Responsive card grid with keyboard-friendly actions.
- Full-screen chart modal instead of inline expansion.
- Dedicated Alert Center page with table editing and bulk actions.
- Better loading/empty/error states for each section.

## Migration Plan
1. Extract logic from Streamlit script into Python service modules.
2. Build FastAPI endpoints around those services.
3. Build React MVP for read flows (markets, tabs, cards, charts).
4. Port alerts CRUD and run engine actions.
5. Port BUY PDF export and access logging.
6. Add tests (API + component + smoke E2E) and optimize performance.

## Security & Config
- Move Telegram credentials to environment variables only.
- Never commit `.env`; keep `.env.example` as template.
- Validate required env vars at startup.
