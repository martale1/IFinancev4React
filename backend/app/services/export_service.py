from __future__ import annotations

from io import BytesIO

import pandas as pd

from app.services.chart_service import build_alligator_figure
from app.services.watchlist_service import load_market_dataframe, prepare_dataframe


def generate_buy_charts_pdf(df_in: pd.DataFrame, bars: int = 70, chart_type: str = "candlestick") -> bytes:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    d = df_in.copy()
    d["Action"] = d["Action"].astype(str).str.upper()
    buy_df = d[d["Action"] == "BUY"].copy()
    if buy_df.empty:
        return b""

    buf = BytesIO()
    with PdfPages(buf) as pdf:
        for _, row in buy_df.iterrows():
            ticker = str(row.get("Ticker", "")).strip()
            if not ticker:
                continue
            fig = None
            try:
                fig = build_alligator_figure(ticker=ticker, bars=bars, chart_type=chart_type)
                if fig is None:
                    continue
                name = str(row.get("Name", "")).strip()
                title = f"{ticker}" + (f" — {name}" if name and name.lower() != "nan" else "")
                fig.suptitle(title, fontsize=14)
                pdf.savefig(fig, bbox_inches="tight")
            finally:
                if fig is not None:
                    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_buy_pdf_for_market(market: str, bars: int = 70, chart_type: str = "candlestick") -> bytes:
    df_raw = load_market_dataframe(market)
    df = prepare_dataframe(df_raw)
    return generate_buy_charts_pdf(df, bars=bars, chart_type=chart_type)
