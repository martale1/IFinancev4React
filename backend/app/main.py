from __future__ import annotations

import os
import sys

# Ensure matplotlib DLLs can be loaded on Windows when running Python directly
if sys.platform == "win32":
    env_dir = r"C:\Users\theoi\anaconda3\envs\IFinanceTA"
    for d in [
        os.path.join(env_dir, "Library", "bin"),
        os.path.join(env_dir, "Library", "mingw-w64", "bin"),
        os.path.join(env_dir, "bin"),
    ]:
        if os.path.exists(d):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

from datetime import datetime
from io import BytesIO
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, FRONTEND_DIST_DIR, MARKETS, PROJECT_ROOT
from app.schemas import (
    AlertToggleRequest,
    AlertUpsertRequest,
    CustomWatchlistAddItemRequest,
    CustomWatchlistCreateRequest,
    CustomWatchlistRemoveItemRequest,
    ExportPdfRequest,
    AiChatRequest,
    AiChatResponse,
    RunEngineRequest,
    WatchlistResponse,
)
from app.ai.service import chat as ai_chat
from app.services.access_log_service import access_log_health
from app.services.alerts_service import (
    build_alerts_df_for_market,
    delete_rule,
    read_rules_file,
    rules_path_for_market,
    run_alert_engine,
    set_rule_enabled,
    upsert_rule,
)
from app.services.chart_service import chart_png_bytes, chart_backtest_png_bytes
from app.services.scanner_service import scan_market, run_vectorbt_backtest, scan_market_realtime_streaming
from app.services.custom_watchlists_service import (
    add_ticker_to_custom_watchlist,
    create_custom_watchlist,
    custom_markets,
    custom_name_from_market,
    custom_watchlist_source_info,
    is_custom_market,
    list_custom_watchlists,
    load_custom_watchlist_dataframe,
    remove_ticker_from_custom_watchlist,
    delete_custom_watchlist,
)
from app.services.export_service import generate_buy_pdf_for_market
from app.services.opportunity_service import rank_opportunities
from app.services.watchlist_service import (
    analysis_source_info_for_market,
    apply_search_and_volume_filters,
    apply_state_filters,
    filter_by_tab,
    load_market_dataframe,
    paginate,
    prepare_dataframe,
    records,
)

app = FastAPI(title="IFinance v4 React Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=bool(CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "ts": datetime.now().isoformat()}


@app.get("/api/markets")
def markets() -> dict[str, Any]:
    return {"markets": MARKETS + custom_markets()}


@app.get("/api/opportunities")
def opportunities(
    market: str = Query(default="ALL"),
    mode: str = Query(default="balanced"),
    limit: int = Query(default=20, ge=5, le=100),
    window: int = Query(default=10, ge=1, le=30),
):
    try:
        return rank_opportunities(market=market, mode=mode, limit=limit, window=window)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/watchlist", response_model=WatchlistResponse)
def watchlist(
    market: str = Query(default="MIB30"),
    tab: str = Query(default="BUY"),
    search: str = Query(default=""),
    min_volume: int = Query(default=2000, ge=0),
    action: str = Query(default=""),
    market_phase: str = Query(default=""),
    trend_phase_detail: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    rank_n: int = Query(default=15, ge=5, le=100),
    only_neg_in_worst: bool = Query(default=True),
) -> WatchlistResponse:
    if (market not in MARKETS) and (not is_custom_market(market)):
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    try:
        if is_custom_market(market):
            wl_name = custom_name_from_market(market)
            source_info = custom_watchlist_source_info(wl_name)
            df = load_custom_watchlist_dataframe(wl_name)
        else:
            source_info = analysis_source_info_for_market(market)
            df_raw = load_market_dataframe(market)
            df = prepare_dataframe(df_raw)
        df = apply_search_and_volume_filters(df, search=search, min_volume=min_volume)
        df = apply_state_filters(df, action=action, market_phase=market_phase, trend_phase_detail=trend_phase_detail)
        dft = filter_by_tab(df, tab, rank_n, only_neg_in_worst=only_neg_in_worst)
        dft_page, total_rows, total_pages = paginate(dft, page, page_size)
        return WatchlistResponse(
            market=market,
            tab=tab,
            source_file=source_info.get("source_file"),
            source_path=source_info.get("source_path"),
            source_updated_at=source_info.get("source_updated_at"),
            page=page,
            page_size=page_size,
            total_rows=total_rows,
            total_pages=total_pages,
            items=records(dft_page),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/watchlist/focus")
def watchlist_focus(market: str, ticker: str) -> dict[str, Any]:
    if (market not in MARKETS) and (not is_custom_market(market)):
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    try:
        if is_custom_market(market):
            wl_name = custom_name_from_market(market)
            df = load_custom_watchlist_dataframe(wl_name)
        else:
            df_raw = load_market_dataframe(market)
            df = prepare_dataframe(df_raw)
        t = ticker.strip().upper()
        found = df[df["Ticker"].astype(str).str.strip().str.upper() == t]
        if found.empty:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found in market '{market}'")
        return {"market": market, "ticker": ticker, "item": records(found.iloc[[0]])[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/charts/{ticker}")
def chart(
    ticker: str,
    bars: int = Query(default=70, ge=10, le=400),
    chart_type: str = Query(default="candlestick"),
    sl1: float | None = Query(default=None),
    sl2: float | None = Query(default=None),
    pb_stop: float | None = Query(default=None),
    pp_level: float | None = Query(default=None),
):
    if chart_type not in ["candlestick", "line"]:
        raise HTTPException(status_code=400, detail="chart_type must be 'candlestick' or 'line'")
    try:
        levels = {"sl1": sl1, "sl2": sl2, "pb_stop": pb_stop, "pp_level": pp_level}
        data = chart_png_bytes(ticker=ticker, bars=bars, chart_type=chart_type, levels=levels)
        if not data:
            raise HTTPException(status_code=404, detail=f"No chart data for ticker '{ticker}'")
        return StreamingResponse(BytesIO(data), media_type="image/png")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/export/buy-pdf")
def export_buy_pdf(req: ExportPdfRequest):
    try:
        data = generate_buy_pdf_for_market(market=req.market, bars=req.bars, chart_type=req.chart_type)
        if not data:
            raise HTTPException(status_code=404, detail="No BUY rows found for selected market.")
        filename = f"BUY_charts_{req.market}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return StreamingResponse(
            BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/alerts/{market}")
def get_alerts(market: str):
    if market not in MARKETS:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    try:
        rules_data = read_rules_file(rules_path_for_market(market))
        table = build_alerts_df_for_market(market)
        return {
            "market": market,
            "rules": rules_data.get("rules", []),
            "defaults": rules_data.get("defaults", {}),
            "version": rules_data.get("version", 1),
            "table": records(table),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/alerts/{market}/upsert")
def post_alert_rule(market: str, req: AlertUpsertRequest):
    if market not in MARKETS:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    try:
        data = upsert_rule(market, req.payload)
        return {"status": "ok", "rules_count": len(data.get("rules", []))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.patch("/api/alerts/{market}/{rule_id}/enabled")
def patch_alert_enabled(market: str, rule_id: str, req: AlertToggleRequest):
    if market not in MARKETS:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    try:
        data = set_rule_enabled(market, rule_id, enabled=req.enabled)
        return {"status": "ok", "rules_count": len(data.get("rules", []))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.delete("/api/alerts/{market}/{rule_id}")
def delete_alert_rule(market: str, rule_id: str):
    if market not in MARKETS:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    try:
        data = delete_rule(market, rule_id)
        return {"status": "ok", "rules_count": len(data.get("rules", []))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/alerts/run")
def run_alerts(req: RunEngineRequest):
    try:
        if req.markets:
            targets = req.markets
        elif req.market:
            targets = [req.market] if req.run_only_this_market else ["MIB30", "Preferite", "ETF", "ETC"]
        else:
            targets = ["MIB30", "Preferite", "ETF", "ETC"]
        results = run_alert_engine(markets_to_run=targets, telegram_channel=req.telegram_channel)
        return {"status": "ok", "markets": targets, "results": results}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "error": f"{type(exc).__name__}: {exc}"})


@app.get("/api/access-log/health")
def access_log_status():
    return access_log_health()


@app.get("/api/custom-watchlists")
def get_custom_watchlists():
    try:
        return {"watchlists": list_custom_watchlists()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/custom-watchlists")
def post_custom_watchlist(req: CustomWatchlistCreateRequest):
    try:
        out = create_custom_watchlist(req.name)
        return {"status": out.get("status", "ok"), "name": out.get("name", req.name)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/custom-watchlists/add-item")
def post_custom_watchlist_add_item(req: CustomWatchlistAddItemRequest):
    try:
        out = add_ticker_to_custom_watchlist(
            name=req.name,
            ticker=req.ticker,
            source_market=req.source_market,
        )
        return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/custom-watchlists/remove-item")
def post_custom_watchlist_remove_item(req: CustomWatchlistRemoveItemRequest):
    try:
        out = remove_ticker_from_custom_watchlist(
            name=req.name,
            ticker=req.ticker,
            source_market=req.source_market,
        )
        return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.delete("/api/custom-watchlists/{name}")
def delete_custom_watchlist_endpoint(name: str):
    try:
        out = delete_custom_watchlist(name)
        return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.post("/api/ai/chat", response_model=AiChatResponse)
async def post_ai_chat(req: AiChatRequest):
    try:
        return await ai_chat(session_id=req.session_id, message=req.message, model=req.model)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/scanner/custom-patterns")
def api_scanner_custom_patterns():
    import yaml
    yaml_path = PROJECT_ROOT / "custom_patterns.yaml"
    if not yaml_path.exists():
        return {"patterns": []}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return {"patterns": data.get("patterns", [])}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore lettura custom_patterns.yaml: {exc}")


@app.post("/api/scanner/custom-patterns/save")
def api_scanner_save_custom_pattern(payload: dict):
    import yaml
    import re
    yaml_path = PROJECT_ROOT / "custom_patterns.yaml"
    required = ["id", "label", "query"]
    if not all(k in payload for k in required):
        raise HTTPException(status_code=400, detail=f"Campi mancanti: {required}")
    
    pat_id = str(payload["id"]).strip().lower().replace(" ", "_")
    # Sanitizzazione ID
    pat_id = re.sub(r'[^\w\.-]', '', pat_id)
    if not pat_id:
        raise HTTPException(status_code=400, detail="ID pattern non valido.")

    try:
        patterns = []
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                patterns = data.get("patterns", [])
        
        # Cerca se esiste già per aggiornarlo, altrimenti aggiungi
        found = False
        new_pattern = {
            "id": pat_id,
            "label": str(payload["label"]).strip(),
            "desc": str(payload.get("desc", "")).strip(),
            "query": str(payload["query"]).strip(),
            "color": str(payload.get("color", "#6b7280")).strip()
        }
        
        for i, p in enumerate(patterns):
            if p.get("id") == pat_id:
                patterns[i] = new_pattern
                found = True
                break
        
        if not found:
            patterns.append(new_pattern)
            
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"patterns": patterns}, f, default_flow_style=False, sort_keys=False)
            
        return {"status": "ok", "pattern": new_pattern}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore durante il salvataggio del pattern: {exc}")


@app.delete("/api/scanner/custom-patterns/{pattern_id}")
def api_scanner_delete_custom_pattern(pattern_id: str):
    import yaml
    yaml_path = PROJECT_ROOT / "custom_patterns.yaml"
    try:
        patterns = []
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                patterns = data.get("patterns", [])
                
        # Filtra via il pattern
        new_patterns = [p for p in patterns if p.get("id") != pattern_id]
        
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"patterns": new_patterns}, f, default_flow_style=False, sort_keys=False)
            
        return {"status": "ok", "deleted_id": pattern_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore durante l'eliminazione del pattern: {exc}")


@app.get("/api/scanner/scan")
def api_scanner_scan(
    market: str = Query(default="MIB30"),
    pattern: str = Query(default="S2"),
    use_sar: bool = Query(default=True),
    use_sma200: bool = Query(default=False),
    lookback: int = Query(default=1, ge=1, le=10),
):
    try:
        if market == "ALL":
            target_markets = ["MIB30", "DAX", "ETC", "ETF", "Preferite"]
            combined_results = []
            for mkt in target_markets:
                mkt_results = scan_market(market=mkt, pattern=pattern, use_sar=use_sar, use_sma200=use_sma200, lookback=lookback)
                for r in mkt_results:
                    r["Market"] = mkt
                combined_results.extend(mkt_results)
            return {"market": market, "pattern": pattern, "results": combined_results}
        else:
            results = scan_market(market=market, pattern=pattern, use_sar=use_sar, use_sma200=use_sma200, lookback=lookback)
            for r in results:
                r["Market"] = market
            return {"market": market, "pattern": pattern, "results": results}
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/scanner/scan-stream")
def api_scanner_scan_stream(
    market: str = Query(default="ALL"),
    pattern: str = Query(default="S2"),
    use_sar: bool = Query(default=True),
    use_sma200: bool = Query(default=False),
    lookback: int = Query(default=1, ge=1, le=10),
):
    """
    Endpoint SSE: emette i risultati della scansione man mano che i ticker vengono
    processati. Utile per pattern custom (Alligator Bull, Golden Cross, ecc.) che
    richiedono download yfinance per ogni ticker.

    Il client legge il corpo come stream di eventi SSE:
      data: {"type": "market_start", "market": "MIB30", "total": 30}
      data: {"type": "result", "data": {...}, "done": 5, "total": 30, "market": "MIB30"}
      data: {"type": "progress", "done": 6, "total": 30, "market": "MIB30"}
      data: {"type": "done"}
    """
    if market == "ALL":
        target_markets = ["MIB30", "DAX", "ETC", "ETF", "Preferite"]
    else:
        target_markets = [market]

    generator = scan_market_realtime_streaming(
        markets_list=target_markets,
        pattern=pattern,
        use_sar=use_sar,
        use_sma200=use_sma200,
        lookback=lookback,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disabilita buffering in nginx
        },
    )



@app.get("/api/scanner/backtest")
def api_scanner_backtest(
    ticker: str,
    pattern: str = Query(default="S2"),
    use_sar: bool = Query(default=True),
    use_sma200: bool = Query(default=False),
):
    try:
        results = run_vectorbt_backtest(
            ticker=ticker,
            pattern=pattern,
            use_sar=use_sar,
            use_sma200=use_sma200
        )
        return results
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@app.get("/api/scanner/backtest/chart")
def api_scanner_backtest_chart(
    ticker: str,
    pattern: str = Query(default="S2"),
    use_sar: bool = Query(default=True),
    use_sma200: bool = Query(default=False),
    bars: int = Query(default=70, ge=10, le=400),
    chart_type: str = Query(default="candlestick"),
):
    try:
        data = chart_backtest_png_bytes(
            ticker=ticker,
            pattern=pattern,
            use_sar=use_sar,
            use_sma200=use_sma200,
            bars=bars,
            chart_type=chart_type
        )
        if not data:
            raise HTTPException(status_code=404, detail=f"No chart data for backtest of ticker '{ticker}'")
        return StreamingResponse(BytesIO(data), media_type="image/png")
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


from pathlib import Path
import pandas as pd
import sys
import subprocess
from pydantic import BaseModel
from app.config import PROJECT_ROOT

MARKET_FILES = {
    "MIB30": "validtickers_IT_MIB30.xlsx",
    "Preferite": "preferite.xlsx",
    "DAX": "validtickers_DE_DAX.xlsx",
    "ETF": "validtickers_IT_ETF.xlsx",
    "ETC": "validtickers_IT_ETC.xlsx",
    "US_Others": "validtickers_US_DOW_NASDAQ.xlsx",
    "US_ETF": "validtickers_US_ETF.xlsx",
}

def get_excel_list_path(market: str) -> Path | None:
    filename = MARKET_FILES.get(market)
    if not filename:
        return None
    return PROJECT_ROOT / "validTickersXLS" / filename

class AddTickerRequest(BaseModel):
    ticker: str
    name: str
    source_market: str | None = None

class RemoveTickerRequest(BaseModel):
    ticker: str | None = None
    tickers: list[str] | None = None
    source_market: str | None = None

@app.get("/api/ticker-lists/{market}")
def get_ticker_list(market: str):
    from app.services.custom_watchlists_service import is_custom_market, custom_name_from_market, read_custom_watchlists
    
    if is_custom_market(market):
        wl_name = custom_name_from_market(market)
        data = read_custom_watchlists()
        watchlists = data.get("watchlists", {}) or {}
        wl_data = watchlists.get(wl_name, {}) or {}
        items = wl_data.get("items", []) or []
        normalized = []
        for it in items:
            normalized.append({
                "Ticker": it.get("ticker", ""),
                "Name": it.get("ticker", ""),  # fallback
                "Source_Market": it.get("source_market", "")
            })
        return {"market": market, "is_custom": True, "items": normalized}
    
    excel_path = get_excel_list_path(market)
    if not excel_path or not excel_path.exists():
        raise HTTPException(status_code=400, detail=f"Mercato '{market}' non supportato o file Excel non trovato.")
    
    try:
        df = pd.read_excel(excel_path)
        for col in df.columns:
            if str(col).lower() == "ticker":
                df.rename(columns={col: "Ticker"}, inplace=True)
            if str(col).lower() == "name":
                df.rename(columns={col: "Name"}, inplace=True)
                
        df["Ticker"] = df["Ticker"].fillna("").astype(str).str.strip()
        df["Name"] = df["Name"].fillna("").astype(str).str.strip()
        
        items = df[["Ticker", "Name"]].to_dict(orient="records")
        return {"market": market, "is_custom": False, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella lettura del file Excel: {e}")

@app.post("/api/ticker-lists/{market}/add")
def add_ticker_to_list(market: str, req: AddTickerRequest):
    from app.services.custom_watchlists_service import is_custom_market, custom_name_from_market, add_ticker_to_custom_watchlist
    
    ticker_clean = req.ticker.strip().upper()
    name_clean = req.name.strip()
    
    if not ticker_clean:
        raise HTTPException(status_code=400, detail="Ticker è obbligatorio.")
        
    if is_custom_market(market):
        wl_name = custom_name_from_market(market)
        source = req.source_market or "MIB30"
        try:
            res = add_ticker_to_custom_watchlist(name=wl_name, ticker=ticker_clean, source_market=source)
            return res
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    excel_path = get_excel_list_path(market)
    if not excel_path or not excel_path.exists():
        raise HTTPException(status_code=400, detail=f"Mercato '{market}' non supportato o file Excel non trovato.")
        
    try:
        df = pd.read_excel(excel_path)
        for col in df.columns:
            if str(col).lower() == "ticker":
                df.rename(columns={col: "Ticker"}, inplace=True)
            if str(col).lower() == "name":
                df.rename(columns={col: "Name"}, inplace=True)
                
        df["Ticker"] = df["Ticker"].fillna("").astype(str).str.strip()
        if ticker_clean in df["Ticker"].str.upper().values:
            return {"status": "exists", "ticker": ticker_clean, "market": market}
            
        new_row = pd.DataFrame([{"Ticker": ticker_clean, "Name": name_clean}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(excel_path, index=False)
        return {"status": "added", "ticker": ticker_clean, "name": name_clean, "market": market}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'aggiunta al file Excel: {e}")

@app.post("/api/ticker-lists/{market}/remove")
def remove_ticker_from_list(market: str, req: RemoveTickerRequest):
    from app.services.custom_watchlists_service import is_custom_market, custom_name_from_market, remove_ticker_from_custom_watchlist
    
    tickers_clean = []
    if req.tickers:
        tickers_clean = [t.strip().upper() for t in req.tickers if t.strip()]
    elif req.ticker:
        tickers_clean = [req.ticker.strip().upper()]
        
    if not tickers_clean:
        raise HTTPException(status_code=400, detail="Ticker o tickers è obbligatorio.")
        
    if is_custom_market(market):
        wl_name = custom_name_from_market(market)
        try:
            removed_count = 0
            for ticker in tickers_clean:
                res = remove_ticker_from_custom_watchlist(name=wl_name, ticker=ticker, source_market=req.source_market)
                if res.get("status") == "removed":
                    removed_count += 1
            return {"status": "removed", "tickers": tickers_clean, "market": market, "removed": removed_count}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    excel_path = get_excel_list_path(market)
    if not excel_path or not excel_path.exists():
        raise HTTPException(status_code=400, detail=f"Mercato '{market}' non supportato o file Excel non trovato.")
        
    try:
        df = pd.read_excel(excel_path)
        for col in df.columns:
            if str(col).lower() == "ticker":
                df.rename(columns={col: "Ticker"}, inplace=True)
            if str(col).lower() == "name":
                df.rename(columns={col: "Name"}, inplace=True)
                
        df["Ticker"] = df["Ticker"].fillna("").astype(str).str.strip()
        before_count = len(df)
        df = df[~df["Ticker"].str.upper().isin(tickers_clean)]
        after_count = len(df)
        removed_count = before_count - after_count
        
        if removed_count == 0:
            return {"status": "not_found", "tickers": tickers_clean, "market": market, "removed": 0}
            
        df.to_excel(excel_path, index=False)
        return {"status": "removed", "tickers": tickers_clean, "market": market, "removed": removed_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la rimozione dal file Excel: {e}")

@app.post("/api/watchlist/regenerate")
def regenerate_watchlist_data():
    try:
        python_executable = sys.executable or "python"
        script_path = PROJECT_ROOT / "main.py"
        subprocess.Popen([python_executable, str(script_path)], cwd=str(PROJECT_ROOT))
        return {"status": "started", "message": "Rigenerazione delle analisi avviata in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Impossibile avviare il processo di rigenerazione: {e}")


import base64
from pydantic import BaseModel

class AnalyzeChartRequest(BaseModel):
    ticker: str
    market: str
    bars: int = 70
    chart_type: str = "candlestick"
    levels: dict | None = None
    model: str | None = None
    analysis_type: str | None = "detailed" # "detailed" or "concise"

@app.post("/api/ai/analyze-chart")
def api_analyze_chart(req: AnalyzeChartRequest):
    import os
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY non trovata nel backend.")
        
    try:
        # 1. Generate chart image bytes
        img_bytes = chart_png_bytes(
            ticker=req.ticker,
            bars=req.bars,
            chart_type=req.chart_type,
            levels=req.levels
        )
        if not img_bytes:
            raise HTTPException(status_code=404, detail=f"Impossibile generare il grafico per il ticker '{req.ticker}'")
            
        # 2. Encode to base64
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        
        # 3. Instantiate OpenAI client
        client = OpenAI(api_key=api_key)
        
        # 4. Call multimodal model
        if req.analysis_type == "concise":
            prompt_text = (
                f"Analizza l'immagine del grafico tecnico allegata per il titolo '{req.ticker}' (Mercato: {req.market}).\n\n"
                "RISPONDI ESCLUSIVAMENTE IN ITALIANO con la seguente struttura FISSA e OBBLIGATORIA in markdown. Sii estremamente sintetico, conciso e operativo (da farsi nell'immediato).\n\n"
                "---\n"
                "### 📘 ANALISI GRAFICA STRUTTURATA SINTETICA — {ticker}\n\n"
                "#### 🔍 QUADRO TECNICO (Massimo 3-4 righe complessive)\n"
                "[Fornisci una sintesi telegrafica dei punti chiave: es. MACD cross recente, RSI neutrale, ADX debole, Alligator piatto]\n\n"
                "#### 🎯 LIVELLI CHIAVE & OPERATIVI\n"
                "- **Supporto**: [Livello di supporto più vicino]\n"
                "- **Resistenza**: [Livello di resistenza più vicino]\n"
                "- **Stop Loss**: [Livello di invalidazione]\n"
                "- **Target**: [Primo target operativo]\n\n"
                "#### 🧠 DECISIONE OPERATIVA IMMEDIATA: [ENTRARE ORA / NON ENTRARE ORA]\n"
                "Specifica chiaramente la tua decisione in maiuscolo.\n\n"
                "**Se ENTRARE ORA**: indica il punto di ingresso e il razionale in una sola frase.\n\n"
                "**Se NON ENTRARE ORA**: spiega il motivo in una sola frase, poi fornisci le condizioni future come blocco JSON:\n\n"
                "**Condizioni d'ingresso future (in formato JSON)**:\n"
                "```json\n"
                "{\n"
                "  \"conditions\": [\n"
                "    { \"indicator\": \"[Indicatore]\", \"trigger\": \"[Trigger]\", \"description\": \"[Breve descrizione]\" }\n"
                "  ]\n"
                "}\n"
                "```\n\n"
                "Usa un tono altamente professionale, editoriale e focalizzato sul risk management. Sii preciso e prudente."
            )
        else:
            prompt_text = (
                f"Analizza l'immagine del grafico tecnico allegata per il titolo '{req.ticker}' (Mercato: {req.market}).\n\n"
                "Il grafico è composto da 5 pannelli (dall'alto in basso):\n"
                "1. Prezzo con Candele e medie Bill Williams Alligator (Jaw blu, Teeth rosso, Lips verde), più eventuali linee di stop (SL1, SL2).\n"
                "2. Volumi con medie MA10/MA5.\n"
                "3. Oscillatori: RSI (giallo), Stoch K (blu), Stoch D (rosso), Williams %R (azzurro chiaro a destra).\n"
                "4. MACD: Linea MACD (blu), Segnale (rosso), Istogramma (verde/rosso).\n"
                "5. ADX (verde) e indicatori direzionali DI+ (blu) / DI- (arancione).\n\n"
                "RISPONDI ESCLUSIVAMENTE IN ITALIANO con la seguente struttura FISSA e OBBLIGATORIA in markdown. Non saltare nessuna sezione.\n\n"
                "---\n"
                "### 📘 ANALISI GRAFICA MULTIMODALE AI — {ticker}\n\n"
                "#### 🔍 CONDIZIONI MINIME DI INGRESSO (Analisi dei 10 Pilastri)\n"
                "Per ciascuno dei 10 punti seguenti, analizza l'immagine del grafico e fornisci una valutazione dettagliata:\n"
                "1. **MACD Bullish Cross**: Analizza il crossover MACD vs Signal, l'orientamento dell'istogramma e quante sedute verdi consecutive vedi.\n"
                "2. **Prezzo vs Resistenza Chiave**: Identifica il livello di resistenza tecnica critica (area di prezzo) e valuta se il prezzo ha chiuso sopra con candela ampia.\n"
                "3. **DI+ vs DI-**: Indica chi ha il controllo (buyer o seller), se DI+ è in accelerazione e DI- in discesa.\n"
                "4. **RSI**: Fornisci il valore stimato dell'RSI e valuta se è sopra o sotto la soglia chiave di 50.\n"
                "5. **Stocastico**: Valuta Stoch K vs Stoch D, la loro posizione rispetto alle soglie 50 e 80.\n"
                "6. **Williams %R**: Analizza il Williams %R (linea azzurra chiara nel pannello oscillatori, scala -100 a 0). Valuta se è in zona ipervenduto (< -80), neutrale (-50) o ipercomprato (> -20). Indica se sta risalendo verso -50 o -20 come segnale anticipatore bullish.\n"
                "7. **Prezzo vs EMA30**: Valuta se il prezzo è sopra o sotto l'EMA30 e se questa sta girando flat/up o è ancora in discesa.\n"
                "8. **Volumi**: Confronta il volume corrente con la media MA10/MA5 e stima la percentuale di incremento o decremento.\n"
                "9. **Alligator**: Analizza la posizione Lips/Teeth/Jaw (Lips > Teeth > Jaw = bullish) e l'apertura progressiva delle linee.\n"
                "10. **ADX**: Indica il livello stimato dell'ADX e se è sopra o sotto 25, e se è crescente o decrescente.\n\n"
                "#### ⏱️ SEQUENZA IDEALE DA MONITORARE\n"
                "- **FASE 1 — Attenzione (Segnali Anticipatori)**: [Indica le condizioni iniziali già presenti o quasi verificate, es. MACD cross imminente, RSI vicino a 50, Stoch in risalita]\n"
                "- **FASE 2 — Entrata Anticipata**: [Rottura di livelli chiave di prezzo, DI+ che supera DI-, volumi che tornano sopra la media]\n"
                "- **FASE 3 — Conferma Forte (Trend Esteso)**: [Alligator in configurazione bullish, EMA30 orientata verso l'alto, ADX > 25 e crescente]\n\n"
                "#### 🎯 LIVELLI PRATICI & OPERATIVI\n"
                "- **Supporto Chiave**: [Livello di supporto orizzontale o dinamico più vicino sotto il prezzo attuale]\n"
                "- **Resistenza Chiave**: [Livello di resistenza più vicino sopra il prezzo attuale]\n"
                "- **Entrata Aggressiva**: [Trigger e range d'ingresso aggressivo]\n"
                "- **Entrata Conservativa**: [Trigger e range d'ingresso conservativo con conferma]\n"
                "- **Primo Target**: [Primo livello di target profit operativo]\n"
                "- **Secondo Target**: [Secondo livello di target profit di medio periodo]\n"
                "- **Invalidazione (Stop Loss)**: [Livello sotto il quale il setup rialzista viene completamente invalidato]\n\n"
                "#### 🧠 VALUTAZIONE INGRESSO: [ENTRARE ORA / NON ENTRARE ORA]\n"
                "Specifica chiaramente la tua decisione in maiuscolo tra le due opzioni.\n\n"
                "**Se ENTRARE ORA**: fornisci un breve razionale e la checklist delle condizioni già verificate.\n\n"
                "**Se NON ENTRARE ORA**: spiega brevemente il motivo, poi fornisci OBBLIGATORIAMENTE le condizioni future come blocco JSON:\n\n"
                "**Condizioni d'ingresso future (in formato JSON)**:\n"
                "```json\n"
                "{\n"
                "  \"conditions\": [\n"
                "    { \"indicator\": \"MACD\", \"trigger\": \"> Signal\", \"description\": \"MACD bullish cross: MACD deve superare la linea Signal\" },\n"
                "    { \"indicator\": \"MACD_Hist\", \"trigger\": \"> 0\", \"description\": \"Istogramma MACD deve girare in positivo con almeno 2 barre verdi crescenti\" },\n"
                "    { \"indicator\": \"Price\", \"trigger\": \"> 21.10\", \"description\": \"Chiusura daily confermata sopra la resistenza chiave con candela ampia\" },\n"
                "    { \"indicator\": \"DI_plus\", \"trigger\": \"> DI_minus\", \"description\": \"DI+ deve superare DI-, confermando il ritorno dei compratori\" },\n"
                "    { \"indicator\": \"RSI\", \"trigger\": \"> 50\", \"description\": \"RSI deve tornare sopra 50 per avviare la fase trend-following\" },\n"
                "    { \"indicator\": \"Stoch_K\", \"trigger\": \"> Stoch_D AND Stoch_K > 50 AND Stoch_K < 80\", \"description\": \"Stocastico conferma: K sopra D e sopra 50, non ancora in ipercomprato\" },\n"
                "    { \"indicator\": \"Williams_R\", \"trigger\": \"> -50\", \"description\": \"Williams %R risale sopra -50: conferma il ritorno di momentum bullish dalla zona di ipervenduto\" },\n"
                "    { \"indicator\": \"Price\", \"trigger\": \"> EMA30\", \"description\": \"Prezzo sopra EMA30, con EMA30 che smette di scendere (flat o up)\" },\n"
                "    { \"indicator\": \"Volume\", \"trigger\": \"> MA10 * 1.30\", \"description\": \"Volume sopra la media MA10 del +30% o più per confermare la rottura\" },\n"
                "    { \"indicator\": \"Alligator\", \"trigger\": \"Lips > Teeth > Jaw\", \"description\": \"Alligator in configurazione bullish con apertura progressiva delle linee\" },\n"
                "    { \"indicator\": \"ADX\", \"trigger\": \"> 25\", \"description\": \"ADX sopra 25 e crescente: il mercato sta entrando in un trend vero\" }\n"
                "  ]\n"
                "}\n"
                "```\n\n"
                "Usa un tono altamente professionale, editoriale e focalizzato sul risk management. Sii preciso e prudente."
            )
        
        model_name = req.model or "gpt-4o"
        kwargs_completions = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sei un analista tecnico e risk manager professionista specializzato nell'analisi grafica avanzata per IFinance. "
                        "Rispondi SEMPRE in italiano, SEMPRE con la struttura markdown richiesta, e NON saltare mai nessuna sezione. "
                        "Quando la decisione è NON ENTRARE ORA, devi SEMPRE includere il blocco JSON con le condizioni future, "
                        "con i valori trigger personalizzati sul grafico specifico analizzato, non valori generici."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.15,
        }
        
        # Reasoning models and newer models do not support max_tokens. They require max_completion_tokens.
        if model_name.startswith(("o1", "o3", "gpt-5")):
            kwargs_completions["max_completion_tokens"] = 2500
        else:
            kwargs_completions["max_tokens"] = 2500

        response = client.chat.completions.create(**kwargs_completions)
        
        output_text = response.choices[0].message.content
        return {"ticker": req.ticker, "analysis": output_text}
        
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore durante l'analisi AI: {exc}")


def _mount_frontend() -> None:
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.exists():
        return

    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def frontend_root():
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend_spa(full_path: str):
        requested_file = (FRONTEND_DIST_DIR / full_path).resolve()
        frontend_root_dir = FRONTEND_DIST_DIR.resolve()
        try:
            requested_file.relative_to(frontend_root_dir)
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found")

        if requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(index_file)


_mount_frontend()
