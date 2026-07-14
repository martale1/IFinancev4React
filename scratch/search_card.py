with open("frontend/src/components/WatchlistCard.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- WatchlistCard.tsx close or percentage variations lines ---")
for idx, line in enumerate(lines, 1):
    if "Close" in line or "PCTV" in line or "pct" in line or "Var" in line:
        print(f"{idx}: {line.strip()}")
