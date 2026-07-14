import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("frontend/src/components/MultiPatternLabPanel.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- MultiPatternLabPanel.tsx dropdown / pattern matches ---")
for idx, line in enumerate(lines, 1):
    if "S2" in line or "S3" in line or "select" in line or "pattern" in line.lower():
        if any(x in line for x in ["option", "value", "const", "let", "set", "tab", "label", "button"]):
            print(f"{idx}: {line.strip()}")
