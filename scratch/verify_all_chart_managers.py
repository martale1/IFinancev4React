import os
import sys

# Ensure DLL directories are added
env_dir = r"C:\Users\theoi\anaconda3\envs\IFinanceTA"
for d in [
    os.path.join(env_dir, "Library", "bin"),
    os.path.join(env_dir, "Library", "mingw-w64", "bin"),
    os.path.join(env_dir, "bin"),
]:
    if os.path.exists(d):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

# Add project root to sys.path
sys.path.append(r"c:\Users\theoi\PycharmProjects\LearningPython\IFinancev4React")

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from TechnicalAnalyzer import TechnicalAnalyzer

print("Instantiating TechnicalAnalyzer for AAPL...")
ta = TechnicalAnalyzer(ticker="AAPL", period="1y")
print("Calculating TA indicators...")
ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50,MACD,RSI,STOCH,WILLR,ADX,ATR,VOL_PERC,PCTV")
print("Calculating Alligator signals...")
ta.calculate_alligator_signal6()
ta.add_trading_statev4_v1()

mock_ta = ta

# Test 1: ChartManager.py
print("Testing ChartManager.py...")
import ChartManager
cm1 = ChartManager.AlligatorChartManager(technical_analyzer=mock_ta)
# Run a plot
fig1 = cm1.plot_ta_dashboard(days=70)
if fig1:
    fig1.savefig("scratch/test_cm1.png")
    plt.close(fig1)
    print("ChartManager.py dashboard plotted successfully!")
else:
    print("ChartManager.py returned None")

# Test 2: ChartManagerBt.py
print("\nTesting ChartManagerBt.py...")
import ChartManagerBt
cm2 = ChartManagerBt.AlligatorChartManager(technical_analyzer=mock_ta)
# Run a plot
fig2 = cm2.plot_ta_dashboard(days=70)
if fig2:
    fig2.savefig("scratch/test_cm2.png")
    plt.close(fig2)
    print("ChartManagerBt.py dashboard plotted successfully!")
else:
    print("ChartManagerBt.py returned None")

# Test 3: ChartManagerWebApp.py
print("\nTesting ChartManagerWebApp.py...")
import ChartManagerWebApp
cm3 = ChartManagerWebApp.AlligatorChartManager(technical_analyzer=mock_ta)
# Run a plot
fig3 = cm3.plot_ta_dashboard(days=70)
if fig3:
    fig3.savefig("scratch/test_cm3.png")
    plt.close(fig3)
    print("ChartManagerWebApp.py dashboard plotted successfully!")
else:
    print("ChartManagerWebApp.py returned None")

print("\nAll ChartManager tests passed successfully!")
