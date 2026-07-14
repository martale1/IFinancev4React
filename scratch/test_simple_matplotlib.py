import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from io import BytesIO

print("Creating simple figure...", flush=True)
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
print("Saving simple figure...", flush=True)
buf = BytesIO()
try:
    fig.savefig(buf, format="png")
    print(f"Saved simple figure! Size: {len(buf.getvalue())}", flush=True)
except BaseException as e:
    import traceback
    traceback.print_exc()
print("Done!", flush=True)
