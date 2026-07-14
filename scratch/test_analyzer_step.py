import sys
sys.path.append('.')
sys.path.append('backend')
import app.config
from TechnicalAnalyzer import TechnicalAnalyzer

print("Instantiating TechnicalAnalyzer for PST.MI...")
ta = TechnicalAnalyzer(ticker="PST.MI", period="2y")
print("Instance created. Dataframe size:", len(ta.dataframe) if ta.dataframe is not None else "None")

print("Calculating TA indicators...")
ta.calculate_TA_Indicators("ALLIGATOR,SAR,EMA_30,EMA_50")
print("Indicators calculated successfully.")
