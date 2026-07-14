import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(6, 4))
x = np.arange(10)
y = np.random.randint(10, 100, size=10)

print("Plotting vlines as bars...", flush=True)
ax.bar(x, y)
# fig.savefig("scratch/test_vlines_output.png")
print("Vlines plotting completed successfully!", flush=True)
