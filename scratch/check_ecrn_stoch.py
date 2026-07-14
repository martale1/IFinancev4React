import yfinance as yf
import talib
import numpy as np
import pandas as pd

ticker = "ECRN.MI"
print(f"Downloading historical data for {ticker}...")
try:
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    if df.empty:
         print("No data downloaded!")
    else:
         print("Downloaded shape:", df.shape)
         if isinstance(df.columns, pd.MultiIndex):
             df.columns = df.columns.get_level_values(0)
             
         close = df['Close'].values.flatten().astype(float)
         high = df['High'].values.flatten().astype(float)
         low = df['Low'].values.flatten().astype(float)
         
         # Stochastic (5, 3, 3)
         slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
         df['Stoch_K'] = slowk
         df['Stoch_D'] = slowd
         
         print("\nLast 10 rows of ECRN.MI prices and Stoch:")
         last_rows = df.tail(10)
         for idx, row in last_rows.iterrows():
              print(f"Date: {idx.strftime('%Y-%m-%d')} | Close: {row['Close']:.4f} | High: {row['High']:.4f} | Low: {row['Low']:.4f} | K: {row['Stoch_K']} | D: {row['Stoch_D']}")
except Exception as e:
    import traceback
    traceback.print_exc()
