import sys
sys.path.append('.')
sys.path.append('backend')
import app.config

# Force Agg backend immediately before any other imports
import os
os.environ["MPLBACKEND"] = "Agg"
import matplotlib
matplotlib.use("Agg", force=True)

from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManager import AlligatorChartManager

print("Instantiating TechnicalAnalyzer...")
ta = TechnicalAnalyzer(ticker="PST.MI", period="2y")
ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")

print("Instantiating AlligatorChartManager...")
cm = AlligatorChartManager(technical_analyzer=ta)
print("ChartManager instantiated.")

print("Calling plot_ta_dashboard...")
fig = cm.plot_ta_dashboard(
    days=70,
    chart_type="candlestick",
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
print("plot_ta_dashboard completed successfully. Fig:", fig)
