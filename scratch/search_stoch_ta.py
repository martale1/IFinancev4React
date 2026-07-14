with open("TechnicalAnalyzer.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "talib.STOCH" in line:
        print(f"talib.STOCH found at line {i+1}: {line.strip()}")
