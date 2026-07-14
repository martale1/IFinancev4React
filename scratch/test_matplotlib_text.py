import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from io import BytesIO

print("Creating figure with NO text/ticks...", flush=True)
fig, ax = plt.subplots()
# Remove all text and ticks
ax.set_title("")
ax.set_xlabel("")
ax.set_ylabel("")
ax.xaxis.set_visible(False)
ax.yaxis.set_visible(False)
for spine in ax.spines.values():
    spine.set_visible(False)

ax.plot([1, 2, 3], [4, 5, 6])

buf = BytesIO()
print("Saving figure with no text...", flush=True)
fig.savefig(buf, format="svg")
print(f"Success! Saved size: {len(buf.getvalue())}", flush=True)
plt.close(fig)
