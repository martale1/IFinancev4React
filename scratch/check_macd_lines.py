import re

with open("ChartManager.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- ChartManager.py MACD lines ---")
for idx, line in enumerate(lines, 1):
    if "MACD" in line or "macd" in line or "axhline" in line or "_add_safe_bar" in line:
        if any(x in line for x in ["0", "zorder", "bar", "axhline", "capstyle", "align"]):
            print(f"{idx}: {line.strip()}")
