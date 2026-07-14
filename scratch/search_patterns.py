import os

search_dir = r"c:\Users\theoi\PycharmProjects\LearningPython\IFinancev4React"
patterns = ["Pattern_S2", "Pattern_S3", "MultiPatternLabPanel"]

results = []
for root, dirs, files in os.walk(search_dir):
    if ".git" in root or ".venv" in root or "node_modules" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith((".py", ".ts", ".tsx", ".css")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        for p in patterns:
                            if p in line:
                                results.append((path, i, p, line.strip()))
            except Exception as e:
                pass

print(f"Found {len(results)} matches:")
for r in results[:100]:
    print(f"{os.path.basename(r[0])}:{r[1]} [{r[2]}] -> {r[3]}")
