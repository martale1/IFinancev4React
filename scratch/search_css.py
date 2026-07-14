with open("frontend/src/styles.css", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- styles.css lines containing price ---")
for idx, line in enumerate(lines, 1):
    if "price" in line or "card-head" in line:
        start = max(1, idx - 3)
        end = min(len(lines), idx + 3)
        print(f"--- line {idx} ---")
        for i in range(start, end + 1):
            print(f"{i}: {lines[i-1].rstrip()}")
