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
    
    # We will simulate plot_ta_dashboard partially to find where the formatter changes!
    fig = cm.plot_ta_dashboard(
        days=70,
        chart_type="candlestick",
        show_signal6_bg=False, # disable background first to prevent crash and see what the formatter is at the end!
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
    
    # Let's inspect the formatter of each axis in the final figure!
    for idx, ax in enumerate(fig.axes):
        print(f"Axis {idx}:")
        print("  Formatter:", ax.xaxis.get_major_formatter())
        print("  Locator:", ax.xaxis.get_major_locator())
        print("  Converter:", ax.xaxis.converter)
        
    print("\nCalling ax_price.fill_between on final figure price axis...")
    ax_price = fig.axes[0]
    try:
        ax_price.fill_between([0.0, 1.0], 5.0, 10.0)
        print("fill_between on final figure price axis SUCCEEDED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
