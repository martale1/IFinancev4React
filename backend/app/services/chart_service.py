from __future__ import annotations

from io import BytesIO
import os
import threading
import time

_CHART_LOCK = threading.Lock()

def _set_headless_matplotlib() -> None:
    """
    Force a non-GUI backend for server-side rendering.
    Prevents tkinter/thread errors under uvicorn on Windows.
    """
    os.environ.setdefault("MPLBACKEND", "Agg")
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
    except Exception:
        pass

def _merge_latest_snapshot(ta, latest_close: float | None, latest_pct_1d: float | None, latest_date: str | None) -> None:
    """Integra la quotazione della watchlist quando la serie daily di Yahoo è indietro."""
    if latest_close is None or ta.dataframe is None or ta.dataframe.empty:
        return

    import pandas as pd

    df = ta.dataframe.copy()
    close = float(latest_close)
    last_close = float(df["Close"].dropna().iloc[-1])
    if abs(close - last_close) < 1e-9:
        return

    recent_closes = df["Close"].dropna().tail(5).astype(float)
    if any(abs(close - value) < 1e-9 for value in recent_closes):
        return

    previous_close = last_close
    if latest_pct_1d is not None and abs(100.0 + float(latest_pct_1d)) > 1e-9:
        previous_close = close / (1.0 + float(latest_pct_1d) / 100.0)

    last_index = pd.Timestamp(df.index[-1])
    if latest_date:
        target_index = pd.Timestamp(latest_date)
        if last_index.tzinfo is not None and target_index.tzinfo is None:
            target_index = target_index.tz_localize(last_index.tzinfo)
        if target_index.normalize() <= last_index.normalize():
            return
    else:
        target_index = last_index + pd.offsets.BDay(1)

    new_row = {column: float("nan") for column in df.columns}
    new_row.update({
        "Open": previous_close,
        "High": max(previous_close, close),
        "Low": min(previous_close, close),
        "Close": close,
        "Adj Close": close,
        "Volume": 0.0,
    })
    df.loc[target_index] = new_row
    ta.dataframe = df.sort_index()


def build_alligator_figure(
    ticker: str,
    bars: int,
    chart_type: str = "candlestick",
    latest_close: float | None = None,
    latest_pct_1d: float | None = None,
    latest_date: str | None = None,
):
    _set_headless_matplotlib()
    from ChartManager import AlligatorChartManager
    from TechnicalAnalyzer import TechnicalAnalyzer

    ta = TechnicalAnalyzer(ticker=ticker, period="2y")
    _merge_latest_snapshot(ta, latest_close, latest_pct_1d, latest_date)
    try:
        ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")
    except Exception:
        pass

    # Calcola EMA9 ed EMA21 se non già presenti nel dataframe
    if ta.dataframe is not None and len(ta.dataframe) > 0:
        try:
            import talib
            import numpy as np
            close_arr = ta.dataframe['Close'].values.flatten().astype(float)
            ta.dataframe['EMA_9']  = talib.EMA(close_arr, timeperiod=9)
            ta.dataframe['EMA_21'] = talib.EMA(close_arr, timeperiod=21)
        except Exception:
            pass

    cm = AlligatorChartManager(technical_analyzer=ta)
    fig = cm.plot_ta_dashboard(
        days=int(bars),
        chart_type=chart_type,
        show_signal6_bg=True,
        show_volume=True,
        volume_ma=(10, 5),
        show_sar=True,
        show_mas=True,
        show_mcs=False,
        show_rsi=True,
        show_stoch=True,
        show_willr=True,
        show_adx=True,
        show_atr_pct_panel=False,
        show_atr_band=False,
        show_tech_score=False,
        figsize=(16, 20),
        dpi=110,
    )
    # EMA9 ed EMA21 sono già nel dataframe (ta.dataframe) e vengono disegnate
    # automaticamente da AlligatorChartManager._add_moving_averages_positions
    return fig


def _build_basic_price_figure(ticker: str, bars: int):
    """
    Lightweight fallback chart if TA dashboard generation fails.
    Uses only Close series from yfinance.
    """
    _set_headless_matplotlib()
    from yfinance_runtime import yf
    import matplotlib.pyplot as plt

    df = yf.Ticker(ticker).history(period="2y", actions=False, auto_adjust=False)
    if df is None or df.empty:
        return None
    df = df.dropna(subset=["Close"]).tail(max(10, int(bars)))
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(14, 6), dpi=110)
    ax.plot(df.index, df["Close"], color="#60a5fa", linewidth=2.0, label="Close")
    ax.set_title(f"{ticker} - Price (fallback)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig


def _add_level_lines(fig, levels: dict | None) -> None:
    if fig is None or not levels:
        return
    if not getattr(fig, "axes", None):
        return
    ax = fig.axes[0]

    color_map = {
        "sl1": "#22c55e",      # green
        "sl2": "#3b82f6",      # blue
        "pb_stop": "#f59e0b",  # amber
        "pp_level": "#ef4444", # red
    }
    label_map = {
        "sl1": "SL1",
        "sl2": "SL2",
        "pb_stop": "PB STOP",
        "pp_level": "PROFIT PROTECT",
    }
    dashed = {"sl1", "pp_level"}
    dotted = {"sl2"}

    for k in ["sl1", "sl2", "pb_stop", "pp_level"]:
        v = levels.get(k)
        try:
            y = float(v)
        except Exception:
            continue
        if y <= 0:
            continue
        ax.axhline(
            y=y,
            color=color_map.get(k, "#93c5fd"),
            linestyle=":" if k in dotted else ("--" if k in dashed else "-."),
            linewidth=1.6,
            alpha=0.9,
            label=f"{label_map.get(k, k)} {y:.3f}",
            zorder=2,
        )
    try:
        ax.legend(loc="upper left", framealpha=0.85)
    except Exception:
        pass


def chart_png_bytes(
    ticker: str,
    bars: int = 70,
    chart_type: str = "candlestick",
    levels: dict | None = None,
    latest_close: float | None = None,
    latest_pct_1d: float | None = None,
    latest_date: str | None = None,
) -> bytes:
    _set_headless_matplotlib()
    import matplotlib.pyplot as plt

    ticker = str(ticker or "").strip()
    fig = None
    try:
        # Matplotlib rendering is not thread-safe. Serialize chart generation.
        with _CHART_LOCK:
            # Server-side retry: provider glitches can be transient.
            last_exc = None
            for _ in range(2):
                try:
                    fig = build_alligator_figure(
                        ticker=ticker,
                        bars=bars,
                        chart_type=chart_type,
                        latest_close=latest_close,
                        latest_pct_1d=latest_pct_1d,
                        latest_date=latest_date,
                    )
                    break
                except Exception as exc:
                    last_exc = exc
                    time.sleep(0.35)

            # Fallback 1: line chart if candlestick path fails.
            if fig is None and str(chart_type).lower() == "candlestick":
                for _ in range(2):
                    try:
                        fig = build_alligator_figure(
                            ticker=ticker,
                            bars=bars,
                            chart_type="line",
                            latest_close=latest_close,
                            latest_pct_1d=latest_pct_1d,
                            latest_date=latest_date,
                        )
                        break
                    except Exception as exc:
                        last_exc = exc
                        time.sleep(0.35)

            # Fallback 2: very simple price chart.
            if fig is None:
                try:
                    fig = _build_basic_price_figure(ticker=ticker, bars=bars)
                except Exception as exc:
                    last_exc = exc
                    fig = None

            if fig is None:
                if last_exc is not None:
                    raise last_exc
                return b""

            _add_level_lines(fig, levels)
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            return buf.getvalue()
    finally:
        if fig is not None:
            plt.close(fig)


def chart_backtest_png_bytes(
    ticker: str,
    pattern: str,
    use_sar: bool = True,
    use_sma200: bool = False,
    bars: int = 70,
    chart_type: str = "candlestick",
) -> bytes:
    _set_headless_matplotlib()
    import matplotlib.pyplot as plt
    from ChartManager import AlligatorChartManager
    from TechnicalAnalyzer import TechnicalAnalyzer
    from app.services.scanner_service import (
        get_historical_data, calculate_all_indicators, get_pattern_rule,
        get_builtin_pattern_rule,
    )
    import vectorbt as vbt
    import numpy as np

    ticker = str(ticker or "").strip()
    fig = None
    try:
        with _CHART_LOCK:
            # 1. Carica i dati storici a 2 anni
            df_hist = get_historical_data(ticker, period="2y")
            if df_hist.empty:
                return b""
                
            df_calc = calculate_all_indicators(df_hist, use_adjusted=True)
            df_clean = df_calc.dropna(subset=['Close', 'SAR']).copy()
            if len(df_clean) < 10:
                return b""
                
            # 2. Ricostruisci le regole di BUY/SELL vectorbt
            custom_query = get_pattern_rule(pattern)
            if custom_query:
                pattern_rule = custom_query
            else:
                pattern_conditions = []
                if pattern in ["S2", "Combined", "S2_or_S3"]:
                    pattern_conditions.append(
                        "(Stoch_K > Stoch_D) & (Stoch_K > 20) & "
                        "(Williams_R > -80) & (Williams_R > Williams_R_shift1) & "
                        "(((Stoch_K > 20) & (Stoch_K_shift1 <= 20)) | "
                        "((Stoch_K > Stoch_D) & (Stoch_K_shift1 <= Stoch_D_shift1)) | "
                        "((Williams_R > -80) & (Williams_R_shift1 <= -80))) & "
                        "(Stoch_K_shift1 < 35)"
                    )
                if pattern in ["S3", "Combined", "S2_or_S3"]:
                    pattern_conditions.append(
                        "(MACD > MACD_Signal) & (MACD_shift1 <= MACD_Signal_shift1) & (MACD > MACD_shift1) & "
                        "(MACD_Hist > 0) & (MACD_Hist > MACD_Hist_shift1)"
                    )
                if pattern == "S4":
                    pattern_conditions.append(
                        "(EMA_9 > EMA_21) & "
                        "(RSI >= 55) & (RSI <= 70) & (RSI > RSI_shift1) & "
                        "(MACD > MACD_Signal) & "
                        "(Volume > Volume_MA20 * 1.5)"
                    )
                if pattern == "S5":
                    pattern_conditions.append(
                        "(RSI < 30) & (Stoch_K > Stoch_D) & (Stoch_K_shift1 <= Stoch_D_shift1)"
                    )
                if pattern == "S6":
                    pattern_conditions.append(
                        "(EMA_30 > EMA_50) & (EMA_30_shift1 <= EMA_50_shift1) & (ADX > 25)"
                    )
                builtin_rule = get_builtin_pattern_rule(pattern)
                if builtin_rule:
                    pattern_conditions.append(builtin_rule)

                if not pattern_conditions:
                    pattern_rule = "(Close > 0)"
                elif pattern == "Combined":
                    pattern_rule = " & ".join(pattern_conditions)
                elif pattern == "S2_or_S3":
                    pattern_rule = " | ".join(f"({c})" for c in pattern_conditions)
                else:
                    pattern_rule = pattern_conditions[0]
                
            buy_conditions = [f"({pattern_rule})"]
            if use_sar:
                buy_conditions.append("(Close > SAR)")
            if use_sma200 and 'SMA200' in df_clean.columns:
                buy_conditions.append("(Close > SMA200)")
                
            buy_rule = " & ".join(buy_conditions)
            is_s7 = pattern in ("S7", "S7_EARLY", "S7_CONFIRMED", "S7_STRONG")
            sell_rule = "SAR 2 sedute o Close < Alligator Teeth" if is_s7 else "(Close < SAR)"
            
            try:
                buy_mask = df_clean.eval(buy_rule).astype(bool)
                if is_s7:
                    below_sar = df_clean['Close'] < df_clean['SAR']
                    sell_mask = (
                        (below_sar & below_sar.shift(1, fill_value=False))
                        | (df_clean['Close'] < df_clean['Alligator_Teeth'])
                    ).fillna(False)
                else:
                    sell_mask = df_clean.eval(sell_rule).astype(bool)
            except Exception:
                return b""
                
            pf = vbt.Portfolio.from_signals(
                close=df_clean['Close'],
                entries=buy_mask,
                exits=sell_mask,
                init_cash=10000.0,
                fees=0.001,
                slippage=0.0005,
                freq="1d"
            )
            
            # 3. Disegna il grafico Alligator
            # Per usare AlligatorChartManager, ha bisogno di un oggetto TechnicalAnalyzer
            ta = TechnicalAnalyzer(ticker=ticker, period="2y")
            ta.dataframe = df_clean.copy()
            
            cm = AlligatorChartManager(technical_analyzer=ta)
            fig = cm.plot_ta_dashboard(
                days=int(bars),
                chart_type=chart_type,
                show_signal6_bg=True,
                show_volume=True,
                volume_ma=(10, 5),
                show_sar=True,
                show_mas=True,
                show_mcs=False,
                show_rsi=True,
                show_stoch=True,
                show_willr=True,
                show_adx=True,
                show_atr_pct_panel=False,
                show_atr_band=False,
                show_tech_score=False,
                figsize=(16, 20),
                dpi=110,
            )
            
            # 4. Sovrapponi i marker di BUY/SELL sul grafico dei prezzi (il primo asse)
            # EMA9 ed EMA21 sono già nel dataframe (df_clean) e vengono disegnate
            # automaticamente da AlligatorChartManager._add_moving_averages_positions
            ax_price = fig.axes[0]
            df_visible = df_clean.tail(int(bars))

            asset_flow = pf.asset_flow()
            buy_indices = np.where((asset_flow.loc[df_visible.index] > 0).values)[0]
            sell_indices = np.where((asset_flow.loc[df_visible.index] < 0).values)[0]
            
            if len(buy_indices) > 0:
                ax_price.scatter(
                    buy_indices,
                    df_visible['Close'].values[buy_indices],
                    marker="^", color="lime", edgecolors="black", s=220, label="BUY (VectorBT)", zorder=15
                )
            if len(sell_indices) > 0:
                ax_price.scatter(
                    sell_indices,
                    df_visible['Close'].values[sell_indices],
                    marker="v", color="red", edgecolors="black", s=220, label="SELL (VectorBT)", zorder=15
                )
                
            # Disegna la linea di Stop Loss (SAR)
            sl_val = float(df_visible['SAR'].iloc[-1])
            ax_price.axhline(
                y=sl_val,
                color="#ef4444",
                linestyle="--",
                linewidth=1.6,
                alpha=0.9,
                label=f"SL (SAR) {sl_val:.3f}",
                zorder=2,
            )
            
            try:
                ax_price.legend(loc="upper left", ncol=2, framealpha=0.85)
            except Exception:
                pass
                
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            return buf.getvalue()
    except Exception as exc:
        print(f"Errore nella generazione del grafico di backtest per {ticker}: {exc}")
        return b""
    finally:
        if fig is not None:
            plt.close(fig)
