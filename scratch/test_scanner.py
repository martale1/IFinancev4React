import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Add backend root to sys.path
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

print("Sys path:", sys.path)

from app.services.scanner_service import scan_single_ticker, run_vectorbt_backtest, scan_market

print("Test: Running scan_single_ticker on 'ENI.MI' for pattern S2...")
res_s2 = scan_single_ticker(ticker="ENI.MI", pattern="S2", use_sar=True, use_sma200=False)
print("Scan S2 result:", res_s2)

print("\nTest: Running scan_market on 'Preferite' for pattern S2...")
try:
    market_res = scan_market(market="Preferite", pattern="S2", use_sar=True, use_sma200=False)
    print("Scan market 'Preferite' completed! Matched count:", len(market_res))
    print("Matched records:", market_res)
except Exception as e:
    print("Scan market failed with error:", e)

print("\nTest: Running run_vectorbt_backtest on 'ENI.MI' for pattern S2...")
try:
    backtest_res = run_vectorbt_backtest(ticker="ENI.MI", pattern="S2", use_sar=True, use_sma200=False)
    print("Backtest keys:", list(backtest_res.keys()))
    print("Backtest metrics Sharpe:", backtest_res["metrics"]["Sharpe Ratio"])
    print("Backtest commentary length:", len(backtest_res["commentary"]))
except Exception as e:
    print("Backtest failed with error:", e)
