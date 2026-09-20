import unittest
from unittest.mock import patch

import pandas as pd

from app.services import scanner_service


def _history_frame(rows: int) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "Open": range(rows),
            "High": range(rows),
            "Low": range(rows),
            "Close": range(rows),
            "Adj Close": range(rows),
            "Volume": [1000] * rows,
        },
        index=dates,
    )


class HistoricalDownloadTest(unittest.TestCase):
    def test_uses_absolute_date_fallback_when_period_returns_one_row(self):
        calls = []

        def fake_download(*args, **kwargs):
            calls.append(kwargs)
            if "period" in kwargs:
                return _history_frame(1)
            return _history_frame(80)

        with patch.object(scanner_service.yf, "download", side_effect=fake_download):
            df = scanner_service.get_historical_data("3BAL.MI", period="2y")

        self.assertEqual(len(df), 80)
        self.assertIn("period", calls[0])
        self.assertIn("start", calls[1])
        self.assertIn("end", calls[1])

    def test_keeps_period_result_when_it_has_enough_rows(self):
        with patch.object(scanner_service.yf, "download", return_value=_history_frame(80)) as download:
            df = scanner_service.get_historical_data("ENI.MI", period="2y")

        self.assertEqual(len(df), 80)
        self.assertEqual(download.call_count, 1)


if __name__ == "__main__":
    unittest.main()
