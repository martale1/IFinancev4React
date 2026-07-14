with open("frontend/src/App.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- App.tsx lines with context ---")
for idx, line in enumerate(lines, 1):
    if "isQuickChart" in line or "setIsQuickChart" in line:
        start = max(1, idx - 4)
        end = min(len(lines), idx + 4)
        print(f"--- line {idx} ---")
        for i in range(start, end + 1):
            print(f"{i}: {lines[i-1].rstrip()}")
