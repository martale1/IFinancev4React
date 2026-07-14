import requests

try:
    print("Sending request to port 8011...")
    res = requests.get("http://127.0.0.1:8011/api/scanner/backtest?ticker=ENI.MI&pattern=S2&use_sar=false&use_sma200=false")
    print("Status:", res.status_code)
    print("Response text:", res.text)
except Exception as e:
    print("Request failed:", e)
