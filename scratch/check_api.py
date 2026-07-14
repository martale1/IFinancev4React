import requests

try:
    print("Testing /api/scanner/scan...")
    res = requests.get("http://127.0.0.1:8010/api/scanner/scan?market=MIB30&pattern=S2&use_sar=false&use_sma200=false")
    print("Scan Status:", res.status_code)
    print("Scan Response:", res.text[:200])
    
    print("\nTesting /api/scanner/backtest...")
    res_bt = requests.get("http://127.0.0.1:8010/api/scanner/backtest?ticker=ENI.MI&pattern=S2&use_sar=false&use_sma200=false")
    print("Backtest Status:", res_bt.status_code)
    print("Backtest Response keys:", list(res_bt.json().keys()) if res_bt.status_code == 200 else res_bt.text)

    print("\nTesting /api/scanner/backtest/chart...")
    res_chart = requests.get("http://127.0.0.1:8010/api/scanner/backtest/chart?ticker=ENI.MI&pattern=S2&use_sar=false&use_sma200=false")
    print("Chart Status:", res_chart.status_code)
    print("Chart Response Length:", len(res_chart.content) if res_chart.status_code == 200 else res_chart.text)

except Exception as e:
    print("Failed to request API:", e)
