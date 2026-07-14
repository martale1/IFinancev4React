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
    
    # 1. Price
    axs[0].plot(df_pos.index, df_pos['Close'])
    # Alligator lines
    for col in ['Alligator_Jaw', 'Alligator_Teeth', 'Alligator_Lips']:
        axs[0].plot(df_pos.index, df_pos[col])
    # SAR
    sar_above = df_pos['SAR'] > df_pos['Close']
    axs[0].scatter(df_pos.index[sar_above], df_pos['SAR'][sar_above])
    # Markers
    signal_mask = df_pos['Signal6'] == 'Uptrend*'
    axs[0].scatter(df_pos.index[signal_mask], df_pos['Close'][signal_mask])
    
    print("After price panel:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    
    # Let's try fill_between here
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between 1 SUCCEEDED!")
    except Exception as e:
        print("  fill_between 1 FAILED!")
        
    # 2. Volumes
    up = df_pos['Close'] >= df_pos['Close'].shift(1)
    down = ~up
    # Wait, how does volume bar plot?
    # In _add_volume_bars_positions:
    # self._add_safe_bar(ax, df_pos.index[up], df_pos['Volume'][up], ...)
    # which does:
    # ax.plot([xi, xi], [0, yi], ...)
    for xi, yi in zip(df_pos.index[up], df_pos['Volume'][up]):
        axs[1].plot([xi, xi], [0, yi], color='green')
        
    print("After volume panel:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between 2 SUCCEEDED!")
    except Exception as e:
        print("  fill_between 2 FAILED!")
        
    # 3. Oscillators
    axs[2].plot(df_pos.index, df_pos['RSI'])
    axs[2].plot(df_pos.index, df_pos['Stoch_K'])
    axs[2].plot(df_pos.index, df_pos['Stoch_D'])
    # Williams_R on secondary axis
    ax_willr = axs[2].twinx()
    ax_willr.plot(df_pos.index, df_pos['Williams_R'])
    
    print("After oscillator panel:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    print("  ax_willr.converter:", ax_willr.xaxis.converter)
    
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between 3 SUCCEEDED!")
    except Exception as e:
        print("  fill_between 3 FAILED!")
        
    # 4. MACD
    axs[3].plot(df_pos.index, df_pos['MACD'])
    axs[3].plot(df_pos.index, df_pos['MACD_Signal'])
    for xi, yi in zip(df_pos.index, df_pos['MACD_Hist']):
        axs[3].plot([xi, xi], [0, yi])
        
    print("After MACD panel:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between 4 SUCCEEDED!")
    except Exception as e:
        print("  fill_between 4 FAILED!")
        
    # 5. ADX
    # Wait, resolve_di_columns
    di_plus, di_minus = cm._resolve_di_columns(df_pos)
    axs[4].plot(df_pos.index, df_pos['ADX'])
    axs[4].plot(df_pos.index, di_plus)
    axs[4].plot(df_pos.index, di_minus)
    
    print("After ADX panel:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between 5 SUCCEEDED!")
    except Exception as e:
        print("  fill_between 5 FAILED!")
