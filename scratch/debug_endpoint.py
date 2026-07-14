import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import api_scanner_backtest
from fastapi.encoders import jsonable_encoder
import json

try:
    print("Calling api_scanner_backtest directly...")
    res = api_scanner_backtest(ticker="ENI.MI", pattern="S2", use_sar=False, use_sma200=False)
    print("Call succeeded! Returned type:", type(res))
    
    print("\nAttempting to serialize with jsonable_encoder...")
    encoded = jsonable_encoder(res)
    print("jsonable_encoder succeeded! Encoded keys:", list(encoded.keys()) if isinstance(encoded, dict) else "Not a dict")
    
    print("\nAttempting to serialize with json.dumps...")
    serialized = json.dumps(encoded)
    print("json.dumps succeeded! Length:", len(serialized))
    
except Exception as e:
    import traceback
    print("Failed with exception:")
    traceback.print_exc()
