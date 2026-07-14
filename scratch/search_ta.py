with open("TechnicalAnalyzer.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- TechnicalAnalyzer.py Pattern / EMA lines ---")
for idx, line in enumerate(lines, 1):
    if "Pattern_" in line or "EMA_9" in line or "EMA_21" in line or "EMA9" in line or "EMA21" in line or "vol_vs_ma20" in line:
        print(f"{idx}: {line.strip()}")
