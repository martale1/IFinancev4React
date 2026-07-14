import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.chart_service import chart_png_bytes

if __name__ == "__main__":
    ticker = "ENEL.MI"
    bars = 70
    chart_type = "line"
    
    try:
        res = chart_png_bytes(ticker=ticker, bars=bars, chart_type=chart_type)
        print("chart_png_bytes (line) length:", len(res))
        with open("enel_line.png", "wb") as f:
            f.write(res)
        print("Saved enel_line.png")
    except Exception as e:
        import traceback
        traceback.print_exc()
