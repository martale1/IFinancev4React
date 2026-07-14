import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.scanner_service import run_vectorbt_backtest

try:
    print("Running backtest with use_sar=False...")
    res = run_vectorbt_backtest(ticker="ENI.MI", pattern="S2", use_sar=False, use_sma200=False)
    print("Success! Keys:", list(res.keys()))
except Exception as e:
    import traceback
    print("Failed with exception:")
    traceback.print_exc()
