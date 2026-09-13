import unittest

import numpy as np
import pandas as pd

from TechnicalAnalyzer import TechnicalAnalyzer


def analyzer_with(rows):
    analyzer = TechnicalAnalyzer.__new__(TechnicalAnalyzer)
    analyzer.dataframe = pd.DataFrame(rows)
    return analyzer


class TechnicalScoreV2Tests(unittest.TestCase):
    def test_same_setup_has_same_score_independently_from_other_rows(self):
        setup = {
            "Close": 110, "EMA_30": 105, "EMA_50": 100,
            "Alligator_Jaw": 101, "Alligator_Teeth": 103, "Alligator_Lips": 106,
            "SAR": 102, "MACD": 2, "MACD_Signal": 1, "MACDH_Trend": "Up",
            "RSI": 60, "RSI_Trend": "Up", "Stoch_K": 65, "Stoch_D": 55,
            "PCTV_5D": 3, "ADX": 28, "PLUS_DI": 30, "MINUS_DI": 18,
            "Vol_Perc_vs_MA20": 10, "ATR_PCT": 2,
        }
        score_alone = analyzer_with([setup]).calculate_technical_score().iloc[0]
        score_with_extremes = analyzer_with([
            setup,
            {**setup, "Close": 70, "RSI": 20, "MACD": -2},
            {**setup, "Close": 150, "RSI": 90, "MACD": 5},
        ]).calculate_technical_score().iloc[0]
        self.assertAlmostEqual(score_alone, score_with_extremes)

    def test_bullish_setup_scores_above_bearish_setup(self):
        bullish = {
            "Close": 105, "EMA_30": 102, "EMA_50": 100, "SAR": 101,
            "MACD": 2, "MACD_Signal": 1, "MACDH_Trend": "Up",
            "RSI": 60, "RSI_Trend": "Up", "Stoch_K": 60, "Stoch_D": 50,
            "PCTV_5D": 3, "ADX": 30, "PLUS_DI": 32, "MINUS_DI": 16,
            "Vol_Perc_vs_MA20": 8, "ATR_PCT": 2,
        }
        bearish = {
            "Close": 95, "EMA_30": 98, "EMA_50": 100, "SAR": 102,
            "MACD": -2, "MACD_Signal": -1, "MACDH_Trend": "Down",
            "RSI": 40, "RSI_Trend": "Down", "Stoch_K": 35, "Stoch_D": 50,
            "PCTV_5D": -3, "ADX": 30, "PLUS_DI": 16, "MINUS_DI": 32,
            "Vol_Perc_vs_MA20": -8, "ATR_PCT": 2,
        }
        scores = analyzer_with([bullish, bearish]).calculate_technical_score()
        self.assertGreater(scores.iloc[0], scores.iloc[1])

    def test_missing_indicators_are_neutral(self):
        analyzer = analyzer_with([{"Close": 100}])
        score = analyzer.calculate_technical_score().iloc[0]
        self.assertTrue(np.isfinite(score))
        self.assertEqual(score, 50.0)

    def test_extension_is_a_separate_penalty(self):
        base = {
            "Close": 104, "EMA_30": 100, "EMA_50": 95,
            "RSI": 68, "Stoch_K": 75, "ATR_PCT": 2,
        }
        extended = {**base, "Close": 118, "RSI": 85, "Stoch_K": 100, "ATR_PCT": 8}
        analyzer = analyzer_with([base, extended])
        analyzer.calculate_technical_score()
        self.assertEqual(analyzer.dataframe.loc[0, "TECH_EXTENSION_PENALTY"], 0.0)
        self.assertGreater(analyzer.dataframe.loc[1, "TECH_EXTENSION_PENALTY"], 15.0)

    def test_structure_is_gradual_not_binary(self):
        rows = [
            {"Close": 100, "EMA_30": 100, "EMA_50": 100, "SAR": 100},
            {"Close": 103, "EMA_30": 101.5, "EMA_50": 100, "SAR": 101},
            {"Close": 106, "EMA_30": 103, "EMA_50": 100, "SAR": 102},
        ]
        analyzer = analyzer_with(rows)
        analyzer.calculate_technical_score()
        structure = analyzer.dataframe["TECH_STRUCTURE"]
        self.assertEqual(structure.iloc[0], 50.0)
        self.assertGreater(structure.iloc[1], structure.iloc[0])
        self.assertGreater(structure.iloc[2], structure.iloc[1])
        self.assertFalse(structure.iloc[1] % 20 == 0)


if __name__ == "__main__":
    unittest.main()
