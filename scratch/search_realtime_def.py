with open("backend/app/services/scanner_service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    if "def scan_market_realtime" in line or "calculate_all_indicators" in line:
        print(f"{idx}: {line.strip()}")
