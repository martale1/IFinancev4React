import sys
import os

# Add parent directory to path to find ChartManager and other files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.chart_service import chart_png_bytes, build_alligator_figure

if __name__ == "__main__":
    ticker = "ENEL.MI"
    bars = 70
    chart_type = "candlestick"
    
    print("Testing build_alligator_figure directly...")
    try:
        fig = build_alligator_figure(ticker, bars, chart_type)
        print("Successfully generated figure object!")
        
        # Save it to a file
        fig.savefig("test_alligator_direct.png", dpi=110, bbox_inches="tight")
        print("Successfully saved test_alligator_direct.png")
    except Exception as e:
        import traceback
        print("FAILED to generate or save direct figure:")
        traceback.print_exc()

    print("\nTesting chart_png_bytes wrapper...")
    try:
        img_bytes = chart_png_bytes(ticker, bars, chart_type)
        if len(img_bytes) > 0:
            print("Successfully generated PNG bytes! Length:", len(img_bytes))
            with open("test_alligator_wrapper.png", "wb") as f:
                f.write(img_bytes)
            print("Saved test_alligator_wrapper.png")
        else:
            print("Returned empty bytes!")
    except Exception as e:
        import traceback
        print("FAILED in chart_png_bytes wrapper:")
        traceback.print_exc()
