import os
import sys
import traceback

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Aggiungi il percorso del progetto
    sys.path.append(os.path.abspath('.'))

    from TechnicalAnalyzer import TechnicalAnalyzer
    from ChartManager import AlligatorChartManager

    ticker = "AAPL"
    print(f"Calcolo indicatori per {ticker}...")
    ta = TechnicalAnalyzer(ticker=ticker, period="1y")
    ta.calculate_TA_Indicators("MACD,RSI,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30")

    print("Generazione dashboard...")
    cm = AlligatorChartManager(technical_analyzer=ta)
    fig = cm.plot_ta_dashboard(
        days=120,
        chart_type="line",
        show_signal6_bg=False,
        show_volume=True,
        volume_ma=(10, 5),
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
        save=True,
        filename="scratch/test_chart_output.png"
    )
    print("Fatto! Grafico salvato in scratch/test_chart_output.png")
except Exception as e:
    print("Errore nel test:")
    traceback.print_exc()
