import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Project path
sys.path.append(os.path.abspath('.'))

from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManager import AlligatorChartManager as ACM

def trace_calls(frame, event, arg):
    if event != 'line':
        return trace_calls
    co = frame.f_code
    func_name = co.co_name
    line_no = frame.f_lineno
    filename = os.path.basename(co.co_filename)
    if 'ChartManager' in filename or 'TechnicalAnalyzer' in filename:
        print(f"[{filename}:{line_no}] {func_name}", flush=True)
    return trace_calls

try:
    print("Initializing TechnicalAnalyzer...", flush=True)
    ta = TechnicalAnalyzer('AAPL', '1y')
    ta.calculate_TA_Indicators('MACD,RSI,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,ATR,ADX')
    ta.calculate_alligator_signal6()
    ta.calculate_technical_score()

    print("\nStarting AlligatorChartManager.plot_ta_dashboard under sys.settrace...", flush=True)
    cm = ACM(ta)
    
    sys.settrace(trace_calls)
    
    cm.plot_ta_dashboard(
        days=120,
        show_willr=True,
        willr_shifted=False,
        show_tech_score=True,
        show_atr_pct_panel=True,
        show_adx=True,
        show_mcs=True
    )
    
    sys.settrace(None)
    print("\nRendering completed successfully!", flush=True)

except Exception as e:
    import traceback
    print("Error occurred:")
    traceback.print_exc()
