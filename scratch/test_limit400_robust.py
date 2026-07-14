import sys
import os
from io import BytesIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.chart_service import build_alligator_figure

if __name__ == "__main__":
    ticker = "ENEL.MI"
    bars = 70
    chart_type = "line"
    
    print("Calling build_alligator_figure...", flush=True)
    fig = build_alligator_figure(ticker=ticker, bars=bars, chart_type=chart_type)
    print(f"Figure created: {fig}", flush=True)
    
    buf = BytesIO()
    print("Calling fig.savefig without bbox_inches...", flush=True)
    try:
        fig.savefig(buf, format="png")
        print(f"fig.savefig succeeded! Bytes size: {len(buf.getvalue())}", flush=True)
    except BaseException as e:
        print("Crashed during fig.savefig!", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(10)
    
    import matplotlib.pyplot as plt
    print("Calling plt.close...", flush=True)
    plt.close(fig)
    print("plt.close succeeded!", flush=True)
    
    print("All steps completed successfully!", flush=True)
