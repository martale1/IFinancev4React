import sys
import traceback
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd
    import datetime

    fig, ax = plt.subplots()
    dates = pd.date_range(start="2026-06-01", periods=5, freq='D')
    values = [10, 20, 15, 30, 25]

    width = 0.8
    half_w = pd.Timedelta(days=width / 2)

    for d, v in zip(dates, values):
        x = [d - half_w, d + half_w]
        print(f"Plotting x={x}, y={v}", flush=True)
        ax.fill_between(x, 0, v, color='blue', alpha=0.7)

    fig.savefig("scratch/test_fill_out.png")
    plt.close(fig)
    print("fill_between test successful!", flush=True)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
