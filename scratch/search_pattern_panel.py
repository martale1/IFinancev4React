with open("frontend/src/components/MultiPatternLabPanel.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- MultiPatternLabPanel.tsx lines containing Close ---")
for idx, line in enumerate(lines, 1):
    if "Close" in line or "ClosePrice" in line:
        if any(x in line for x in ["div", "span", "p", "className", "style"]):
            print(f"{idx}: {line.strip()}")
