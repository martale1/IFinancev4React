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
    fig, ax = plt.subplots()
    print("Initial formatter:", ax.xaxis.get_major_formatter())
    print("Initial locator:", ax.xaxis.get_major_locator())
    print("Initial converter:", ax.xaxis.converter)
    
    # Let's plot Close price
    df_pos = cm._convert_to_positions(ta.dataframe.tail(70))
    print("Plotting Close price with integer index...")
    ax.plot(df_pos.index, df_pos['Close'])
    print("Formatter after plot:", ax.xaxis.get_major_formatter())
    print("Locator after plot:", ax.xaxis.get_major_locator())
    print("Converter after plot:", ax.xaxis.converter)
    
    # Let's add candlesticks
    print("Adding candlesticks...")
    cm._add_candlesticks(ax, ta.dataframe.tail(70))
    print("Formatter after candlesticks:", ax.xaxis.get_major_formatter())
    print("Converter after candlesticks:", ax.xaxis.converter)

    # Let's call ax.fill_between
    print("Calling ax.fill_between...")
    try:
        ax.fill_between([0.0, 1.0], 5.0, 10.0)
        print("fill_between SUCCEEDED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
