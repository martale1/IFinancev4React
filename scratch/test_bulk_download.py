import yfinance as yf
import pandas as pd
import numpy as np

tickers = ["AAPL", "MSFT", "BPSO.MI", "C73.MI"] # two valid, two delisted/failed

print("Downloading in bulk...")
data = yf.download(tickers, period="2y", group_by="ticker", progress=False, auto_adjust=False, threads=True)

print("Columns:", data.columns)
print("Is MultiIndex?", isinstance(data.columns, pd.MultiIndex))

if isinstance(data.columns, pd.MultiIndex):
    for ticker in tickers:
        print(f"\nTicker: {ticker}")
        if ticker in data.columns.levels[0]:
            df_ticker = data[ticker].dropna(how="all")
            print(f"Loaded rows: {len(df_ticker)}")
            if len(df_ticker) > 0:
                print("First row close price:", df_ticker['Close'].iloc[0])
        else:
            print("Not found in levels[0]")
else:
    print("Not a MultiIndex columns dataframe")
