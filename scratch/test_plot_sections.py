import sys
sys.path.append('.')
sys.path.append('backend')
import app.config

import os
os.environ["MPLBACKEND"] = "Agg"
import matplotlib
matplotlib.use("Agg", force=True)

from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManager import AlligatorChartManager

print("Instantiating TechnicalAnalyzer...")
ta = TechnicalAnalyzer(ticker="PST.MI", period="2y")
ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")

cm = AlligatorChartManager(technical_analyzer=ta)

# Let's test with minimal panels first to see if it succeeds!
print("Calling plot_ta_dashboard with minimal panels...")
fig = cm.plot_ta_dashboard(
    days=70,
    chart_type="candlestick",
    show_signal6_bg=False,
    show_volume=False,
    show_sar=False,
    show_mas=False,
    show_mcs=False,
    show_rsi=False,
    show_stoch=False,
    show_willr=False,
    show_adx=False,
    show_atr_pct_panel=False,
    show_atr_band=False,
    show_tech_score=False,
    figsize=(16, 20),
    dpi=110,
)
print("Minimal panels call succeeded!")
