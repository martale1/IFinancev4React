import os
import sys

# Prepend conda environment DLL directories
env_dir = r"C:\Users\theoi\anaconda3\envs\IFinanceTA"
dll_dirs = [
    os.path.join(env_dir, "Library", "bin"),
    os.path.join(env_dir, "Library", "mingw-w64", "bin"),
    os.path.join(env_dir, "bin"),
]

for d in dll_dirs:
    if os.path.exists(d):
        print(f"Adding DLL directory: {d}")
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from io import BytesIO

print("Creating simple figure...", flush=True)
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
ax.set_title("Test Title")
print("Saving simple figure...", flush=True)
buf = BytesIO()
try:
    fig.savefig(buf, format="png")
    print(f"Success! Saved size: {len(buf.getvalue())}", flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
print("Done!", flush=True)
