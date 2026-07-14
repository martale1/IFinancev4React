import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ChartManager import AlligatorChartManager
from TechnicalAnalyzer import TechnicalAnalyzer
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if __name__ == "__main__":
    ticker = "ENEL.MI"
    ta = TechnicalAnalyzer(ticker=ticker, period="2y")
    ta.dataframe = pd.read_parquet(os.path.join(os.path.dirname(__file__), "../cache/ENEL.MI_2y_1d.parquet"))
    
    cm = AlligatorChartManager(technical_analyzer=ta)
    
    # We will simulate plot_ta_dashboard step by step to find exactly where fill_between fails!
    # Let's run it with show_signal6_bg=True to catch the exact state during the crash
    try:
        fig = cm.plot_ta_dashboard(
            days=70,
            chart_type="candlestick",
            show_signal6_bg=True,
            show_volume=True,
            show_sar=True,
            show_mas=True,
            show_mcs=False,
            show_rsi=True,
            show_stoch=True,
            show_willr=True, # Wait, show_willr defaults to True!
            show_adx=True,
            show_atr_pct_panel=False,
            show_atr_band=False,
            show_tech_score=False,
            figsize=(16, 20),
            dpi=110,
        )
        print("plot_ta_dashboard SUCCEEDED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
