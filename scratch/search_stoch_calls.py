with open("TechnicalAnalyzer.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "_calculate_stochastic" in line:
        print(f"_calculate_stochastic found at line {i+1}: {line.strip()}")
