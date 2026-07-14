import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.chart_service import chart_png_bytes

if __name__ == "__main__":
    ticker = "ZAL.DE"  # Let's try ZAL.DE since it was in the walkthrough logs!
    bars = 70
    chart_type = "candlestick"
    
    # Try to generate the chart via chart_png_bytes
    try:
        res = chart_png_bytes(ticker=ticker, bars=bars, chart_type=chart_type)
        print("chart_png_bytes length:", len(res))
        
        # Save it
        with open("zalando.png", "wb") as f:
            f.write(res)
        print("Saved zalando.png")
    except Exception as e:
        import traceback
        traceback.print_exc()
