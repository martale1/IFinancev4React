import pandas as pd
from pathlib import Path

analyses_dir = Path(r"c:\Users\theoi\PycharmProjects\LearningPython\IFinancev4React\analyses")
file_path = analyses_dir / "MIB30_TA_Analyses.xlsx"

if file_path.exists():
    print(f"Reading {file_path.name}...")
    df = pd.read_excel(file_path)
    print("Columns in Excel:")
    cols = sorted(list(df.columns))
    for c in cols:
        print(f"  - {c}")
else:
    print(f"File {file_path} does not exist!")
