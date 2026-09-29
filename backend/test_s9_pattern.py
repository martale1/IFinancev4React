import unittest
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.scanner_service import calculate_all_indicators


class SelloffReboundPatternTests(unittest.TestCase):
    def _frame(self, rebound: bool) -> pd.DataFrame:
        dates = pd.date_range("2026-01-01", periods=90, freq="B")
        close = np.full(90, 100.0)
        close[-12:-1] = [100, 98, 96, 94, 92, 90, 88, 86, 84, 82, 80]
        close[-1] = 86 if rebound else 79
        open_ = close.copy()
        open_[-12:-1] = close[-12:-1] + 1.0
        open_[-1] = 80.0
        high = np.maximum(open_, close) + 0.5
        low = np.minimum(open_, close) - 0.5
        volume = np.full(90, 1_000_000.0)
        volume[-1] = 1_600_000.0
        return pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
            index=dates,
        )

    def test_confirmed_rebound_after_red_candle_selloff(self):
        result = calculate_all_indicators(self._frame(rebound=True), use_adjusted=False)
        last = result.iloc[-1]
        self.assertGreaterEqual(last["Red_Candles_6"], 4)
        self.assertLessEqual(last["Selloff_Return_10_Pct"], -7)
        self.assertTrue(bool(last["Selloff_Rebound_Early_Trigger"]))
        self.assertTrue(bool(last["Selloff_Rebound_Confirmed_Trigger"]))

    def test_continuing_decline_is_not_a_rebound(self):
        result = calculate_all_indicators(self._frame(rebound=False), use_adjusted=False)
        last = result.iloc[-1]
        self.assertFalse(bool(last["Selloff_Rebound_Early_Trigger"]))
        self.assertFalse(bool(last["Selloff_Rebound_Confirmed_Trigger"]))


if __name__ == "__main__":
    unittest.main()
