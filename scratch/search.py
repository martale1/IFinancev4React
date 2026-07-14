import os
import re

patterns = [
    re.compile(r'multiprocessing'),
    re.compile(r'ProcessPoolExecutor'),
    re.compile(r'Pool\('),
    re.compile(r'Process\(')
]

exclude_dirs = {'.venv', 'node_modules', 'dist', '.git', '__pycache__', 'cache'}

root_dir = "c:\\Users\\theoi\\PycharmProjects\\LearningPython\\IFinancev4React"

for dirpath, dirnames, filenames in os.walk(root_dir):
    # modify dirnames in-place to prune them
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
    for filename in filenames:
        if filename.endswith('.py'):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        for p in patterns:
                            if p.search(line):
                                print(f"{filename}:{i}: {line.strip()}")
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
