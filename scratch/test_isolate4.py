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
    ta.calculate_alligator_signal6()
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
    
    # 2. Volumes
    up = df_pos['Close'] >= df_pos['Close'].shift(1)
    down = ~up
    for xi, yi in zip(df_pos.index[up], df_pos['Volume'][up]):
        axs[1].plot([xi, xi], [0, yi], color='green')
        
    # 3. Oscillators
    axs[2].plot(df_pos.index, df_pos['RSI'])
    axs[2].plot(df_pos.index, df_pos['Stoch_K'])
    axs[2].plot(df_pos.index, df_pos['Stoch_D'])
    # Williams_R on secondary axis
    ax_willr = axs[2].twinx()
    ax_willr.plot(df_pos.index, df_pos['Williams_R'])
    
    # 4. MACD
    axs[3].plot(df_pos.index, df_pos['MACD'])
    axs[3].plot(df_pos.index, df_pos['MACD_Signal'])
    for xi, yi in zip(df_pos.index, df_pos['MACD_Hist']):
        axs[3].plot([xi, xi], [0, yi])
        
    # 5. ADX
    di_plus, di_minus = cm._resolve_di_columns(df_pos)
    axs[4].plot(df_pos.index, df_pos['ADX'])
    axs[4].plot(df_pos.index, di_plus)
    axs[4].plot(df_pos.index, di_minus)
    
    # Let's add candlesticks
    cm._add_candlesticks(axs[0], ta.dataframe.tail(70))
    
    # Let's check the date axis setup!
    cm._setup_date_axis(axs[5], ta.dataframe.tail(70), df_pos.index)
    
    # What about final formatting/rendering or legends?
    cm._setup_dual_legends(axs[0], True)
    
    print("After all setup:")
    print("  axs[0].converter:", axs[0].xaxis.converter)
    
    try:
        axs[0].fill_between([0, 1], 10, 20)
        print("  fill_between final SUCCEEDED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
