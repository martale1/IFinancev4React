import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(os.path.abspath('.'))
from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManager import AlligatorChartManager

ta = TechnicalAnalyzer('AAPL', '1y')
ta.calculate_TA_Indicators('MACD,RSI,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30')
cm = AlligatorChartManager(ta)

df = cm.ta.dataframe.copy().tail(120)
df_pos = cm._convert_to_positions(df)

print("Columns in df_pos:", list(df_pos.columns))
print("RSI null count:", df_pos['RSI'].isnull().sum())
print("Stoch_K null count:", df_pos['Stoch_K'].isnull().sum())
print("Stoch_D null count:", df_pos['Stoch_D'].isnull().sum())

fig, ax = plt.subplots(figsize=(10, 4))
print("Plotting RSI line...")
ax.plot(df_pos.index, df_pos['RSI'], label='RSI')
print("RSI line plotted!")

print("Calling axhline replacement (plot)...")
ax.plot([df_pos.index[0], df_pos.index[-1]], [70, 70], color='purple', linestyle='--', linewidth=1)
print("ax.plot line plotted!")

print("Plotting Stoch K line...")
ax.plot(df_pos.index, df_pos['Stoch_K'], label='Stoch K')
print("Stoch K line plotted!")

print("Plotting Stoch D line...")
ax.plot(df_pos.index, df_pos['Stoch_D'], label='Stoch D')
print("Stoch D line plotted!")

print("All plots successful!")
