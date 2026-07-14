import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Project path
sys.path.append(os.path.abspath('.'))

try:
    print("1. Initializing TechnicalAnalyzer...", flush=True)
    from TechnicalAnalyzer import TechnicalAnalyzer
    from ChartManager import AlligatorChartManager as ACM
    from ChartManagerBt import AlligatorChartManager as ACMBt
    from ChartManagerWebApp import AlligatorChartManager as ACMWebApp

    print("2. Downloading data and calculating indicators...", flush=True)
    ta = TechnicalAnalyzer('AAPL', '1y')
    ta.calculate_TA_Indicators('MACD,RSI,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,ATR,ADX')
    
    print("3. Calculating Alligator Signal6...", flush=True)
    ta.calculate_alligator_signal6()
    
    print("4. Calculating Technical Score...", flush=True)
    ta.calculate_technical_score()

    managers = [
        ("ChartManager.py (Standard)", ACM(ta)),
        ("ChartManagerBt.py (Backtest)", ACMBt(ta)),
        ("ChartManagerWebApp.py (WebApp)", ACMWebApp(ta))
    ]

    for name, manager in managers:
        print(f"\n--- Testing {name} ---", flush=True)
        
        # Test willr_shifted = False
        print("  Running plot_ta_dashboard(willr_shifted=False)...", flush=True)
        fig1 = manager.plot_ta_dashboard(
            days=120,
            show_willr=True,
            willr_shifted=False,
            show_tech_score=True,
            show_atr_pct_panel=True,
            show_adx=True,
            show_mcs=True
        )
        if fig1 is not None:
            plt.close(fig1)
        print("  [OK] willr_shifted=False rendering successful!", flush=True)

        # Test willr_shifted = True
        print("  Running plot_ta_dashboard(willr_shifted=True)...", flush=True)
        fig2 = manager.plot_ta_dashboard(
            days=120,
            show_willr=True,
            willr_shifted=True,
            show_tech_score=True,
            show_atr_pct_panel=True,
            show_adx=True,
            show_mcs=True
        )
        if fig2 is not None:
            plt.close(fig2)
        print("  [OK] willr_shifted=True rendering successful!", flush=True)

    print("\n[SUCCESS] ALL TESTS COMPLETED SUCCESSFULLY! No segfaults or Matplotlib crashes occurred.", flush=True)

except Exception as e:
    import traceback
    print("\n[ERROR] Error encountered during test execution:", flush=True)
    traceback.print_exc()
    sys.exit(1)
