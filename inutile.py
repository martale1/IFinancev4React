import yfinance as yf
import talib
import numpy as np

df = yf.download(
    "AAPL",
    period="6mo",
    interval="1d",
    auto_adjust=False
)

close = df["Close"].squeeze().to_numpy(dtype="float64")

print(close.shape)   # deve essere tipo: (126,)

df["RSI"] = talib.RSI(close, timeperiod=14)

macd, macd_signal, macd_hist = talib.MACD(
    close,
    fastperiod=12,
    slowperiod=26,
    signalperiod=9
)

df["MACD"] = macd
df["MACD_SIGNAL"] = macd_signal
df["MACD_HIST"] = macd_hist
df["SMA20"] = talib.SMA(close, timeperiod=20)

print(df[["Close", "RSI", "MACD", "MACD_SIGNAL", "MACD_HIST", "SMA20"]].tail(10))