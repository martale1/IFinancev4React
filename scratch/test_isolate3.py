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
    df = pd.read_parquet("cache/ENEL.MI_2y_1d.parquet")
    ta = TechnicalAnalyzer(ticker="ENEL.MI", period="2y")
    ta.dataframe = df
    ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")
    cm = AlligatorChartManager(technical_analyzer=ta)
    
    # We will simulate the plot step-by-step
    fig, axs = plt.subplots(6, 1, sharex=True)
    df_pos = cm._convert_to_positions(ta.dataframe.tail(70))
    
    # Let's add candlesticks
    cm._add_candlesticks(axs[0], ta.dataframe.tail(70))
    
    # Let's check the date axis setup!
    # In plot_ta_dashboard:
    # bottom_ax = axes[-1]
    # self._setup_date_axis(bottom_ax, df0, df_pos.index)
    cm._setup_date_axis(axs[5], ta.dataframe.tail(70), df_pos.index)
    
    # What about final formatting/rendering or legends?
    # In plot_ta_dashboard:
    # self._setup_dual_legends(ax_price, show_background)
    cm._setup_dual_legends(axs[0], True)
    
    print("After all setup:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between final SUCCEEDED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
