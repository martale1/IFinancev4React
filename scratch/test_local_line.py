import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ChartManager import AlligatorChartManager
from TechnicalAnalyzer import TechnicalAnalyzer
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if __name__ == "__main__":
    try:
        print("1. Loading parquet data...")
        df = pd.read_parquet("cache/ENEL.MI_2y_1d.parquet")
        print("Data loaded successfully, shape:", df.shape)
        
        print("2. Initializing TechnicalAnalyzer...")
        ta = TechnicalAnalyzer(ticker="ENEL.MI", period="2y")
        ta.dataframe = df
        
        print("3. Calculating indicators...")
        ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")
        print("Indicators calculated successfully!")
        
        print("4. Initializing AlligatorChartManager...")
        cm = AlligatorChartManager(technical_analyzer=ta)
        
        print("5. Plotting dashboard (line)...")
        fig = cm.plot_ta_dashboard(
            days=70,
            chart_type="line",
            show_signal6_bg=False,
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
        
        print("6. Saving figure...")
        fig.savefig("enel_local_line.png", dpi=110, bbox_inches="tight")
        print("Figure saved successfully to enel_local_line.png")
        
    except Exception as e:
        print("!!! EXCEPTION RAISED !!!")
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
    print("Test local line SUCCEEDED!")
