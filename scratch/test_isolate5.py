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
    # Load from parquet
    df = pd.read_parquet("cache/ENEL.MI_2y_1d.parquet")
    ta = TechnicalAnalyzer(ticker="ENEL.MI", period="2y")
    ta.dataframe = df
    
    # We will compute indicators. Wait, what indicators does chart_service compute?
    # build_alligator_figure does: ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")
    ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")
    
    cm = AlligatorChartManager(technical_analyzer=ta)
    
    print("Testing plot_ta_dashboard wrapper with show_signal6_bg=True...")
    try:
        fig = cm.plot_ta_dashboard(
            days=70,
            chart_type="line",
            show_signal6_bg=True,
            show_volume=True,
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
        print("plot_ta_dashboard completed successfully!")
    except Exception as e:
        import traceback
        traceback.print_exc()
