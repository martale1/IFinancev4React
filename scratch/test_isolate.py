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
    fig, axs = plt.subplots(2, 1, sharex=True)
    
    print("Step 1: Check formatter after init:")
    print("  ax0 formatter:", axs[0].xaxis.get_major_formatter())
    print("  ax0 converter:", axs[0].xaxis.converter)
    
    # Let's plot Close on axs[0]
    df_pos = cm._convert_to_positions(ta.dataframe.tail(70))
    axs[0].plot(df_pos.index, df_pos['Close'])
    print("Step 2: Check formatter after plot on ax0:")
    print("  ax0 formatter:", axs[0].xaxis.get_major_formatter())
    print("  ax0 converter:", axs[0].xaxis.converter)
    
    # Let's plot volume on axs[1]
    axs[1].bar(df_pos.index, df_pos['Volume'])
    print("Step 3: Check formatter after bar on ax1:")
    print("  ax0 formatter:", axs[0].xaxis.get_major_formatter())
    print("  ax0 converter:", axs[0].xaxis.converter)
    
    # Let's call ax.set_xticklabels with date strings on axs[1] (simulating _setup_date_axis)
    # Wait, is _setup_date_axis called before or after? In the dashboard it's called AFTER fill_between.
    # Let's call fill_between on axs[0]
    print("Step 4: Calling axs[0].fill_between...")
    try:
        axs[0].fill_between([0.0, 1.0], 5.0, 10.0)
        print("  axs[0].fill_between SUCCEEDED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        
    # Let's see what happens if we set formatting on axs[1] first
    print("Step 5: Simulating _setup_date_axis on axs[1]...")
    axs[1].set_xticks([0, 10, 20])
    # Wait, did we plot anything else?
