import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from io import BytesIO

def test_format(fmt):
    print(f"\n--- Testing format: {fmt} ---", flush=True)
    try:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6])
        ax.set_title("Test Title")
        buf = BytesIO()
        print("Saving...", flush=True)
        fig.savefig(buf, format=fmt)
        print(f"Success! Saved size: {len(buf.getvalue())}", flush=True)
        plt.close(fig)
    except Exception as e:
        print(f"Caught exception: {e}", flush=True)

test_format("svg")
test_format("pdf")
test_format("png")
print("\nAll tests completed without crashing (if we see this).", flush=True)
