import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.scanner_service import run_vectorbt_backtest
import math

res = run_vectorbt_backtest(ticker="ENI.MI", pattern="S2", use_sar=False, use_sma200=False)
metrics = res["metrics"]

print("Metrics:")
for k, v in metrics.items():
    print(f"  {k}: {v} (type: {type(v)})")
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        print(f"    !!! WARNING: {k} is NaN or Inf !!!")
