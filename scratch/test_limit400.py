import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.chart_service import chart_png_bytes

if __name__ == "__main__":
    ticker = "ENEL.MI"
    bars = 400
    chart_type = "line" # use line to prevent Rectangle crash on Windows
    
    print(f"Testing chart generation with bars={bars}...")
    try:
        res = chart_png_bytes(ticker=ticker, bars=bars, chart_type=chart_type)
        print("chart_png_bytes length:", len(res))
        if len(res) > 0:
            with open("enel_400.png", "wb") as f:
                f.write(res)
            print("Successfully saved enel_400.png!")
        else:
            print("Empty result!")
            sys.exit(3)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(4)
    print("Backend test completed successfully!")
