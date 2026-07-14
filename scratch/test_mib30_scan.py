import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

print("Sys path:", sys.path)

from app.services.scanner_service import scan_market

print("Test: Running scan_market on 'MIB30' for pattern S2...")
try:
    market_res = scan_market(market="MIB30", pattern="S2", use_sar=False, use_sma200=False)
    print("Scan market 'MIB30' completed! Matched count:", len(market_res))
    print("Matched records:", market_res)
except Exception as e:
    import traceback
    print("Scan market failed with error:")
    traceback.print_exc()
