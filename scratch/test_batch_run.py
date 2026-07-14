import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import runTA_indicators
import pandas as pd

try:
    print("Running runTA_indicators on 'Preferite' with numItems=2...")
    df = runTA_indicators(market='Preferite', numItems=2, generateSignal=True, generateScoring=True)
    print("Success! Return type:", type(df))
    print("DataFrame shape:", df.shape)
    print("New columns in returned DataFrame:")
    new_cols = ['Pattern_S2_Match', 'Pattern_S3_Match', 'Pattern_Combined_Match', 'SAR_Filter_Ok', 'SMA200', 'SMA200_Filter_Ok']
    for col in new_cols:
        if col in df.columns:
            print(f"  - {col}: present, first values: {df[col].tolist()}")
        else:
            print(f"  - {col}: !!! MISSING !!!")
except Exception as e:
    import traceback
    print("Failed with exception:")
    traceback.print_exc()
