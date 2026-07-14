with open("TechnicalAnalyzer.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def calculate_TA_Indicators" in line:
        print(f"calculate_TA_Indicators found at line {i+1}")
    if "def add_trading_statev4_v1" in line:
        print(f"add_trading_statev4_v1 found at line {i+1}")
