import sys
sys.path.append('.')
sys.path.append('backend')
import app.config
from TechnicalAnalyzer import TechnicalAnalyzer

print("Instantiating TechnicalAnalyzer...")
ta = TechnicalAnalyzer(ticker="PST.MI", period="2y")

print("Calculating ALL indicators...")
# This lists all indicators that could be requested
indicators_to_test = "MACD,ALLIGATOR,RSI,STOCH,WILLR,SAR,EMA_30,EMA_50,ADX,ATR"
ta.calculate_TA_Indicators(indicators_to_test)
print("All indicators calculated successfully!")
