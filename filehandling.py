import os
from pathlib import Path

import pandas as pd
'''' 
Questa funzione recupera i valid ticker da file excel.
ETC: si usa la funzione getValidETC(0) chiamata in fase di inizializzazione per settare ETCNames, ETCTickers ed ETCDf 
'''
class fileHandling:
  def __init__(self, path=None):
    local_path = Path(__file__).resolve().parent / 'validTickersXLS'
    selected_path = Path(path).expanduser() if path else local_path
    if not selected_path.exists():
      selected_path = local_path
    self.path = str(selected_path.resolve()) + os.sep

    self.ETFNames=None
    self.ETFTickers=None

    self.US_ETFTickers=None
    self.US_ETFNames=None

    self.US_OthersTickers=None
    self.US_OthersNames=None

    self.MIB30Names=None
    self.MIB30Tickers=None

    self.ETCTickers = None
    self.ETCNames = None
    self.ETCDf=None

    self.PreferiteTickers = None
    self.PreferiteNames = None

    self.DAXTickers = None
    self.DAXNames = None

    self.CryptoTickers = None
    self.CryptoNames = None

    self.getValidETC(0)
    self.getValidMIB30(0)
    self.getValidTickerETF(0)
    self.getValidPreferite(0)
    self.getValidUS_ETF(0)
    self.getValidUS_Others(0)
    self.getValidDAX(0)
    self.getValidCrypto(0)

    # Define the path to the Excel file

  def getValidPreferite(self, nTicker=10):
    # Mount Google Drive
    # Define the path to the Excel file
    filename = 'preferite.xlsx'
    file_path = self.path + filename
    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path)

    # Assuming 'ticker' is the name of the column containing tickers
    if nTicker == 0:
      ne = len(df)
    else:
      ne = nTicker
    self.PreferiteTickers = df['Ticker'].head(ne).tolist()
    self.PreferiteNames = df['Name'].head(ne).tolist()

  def getValidUS_Others(self,nTicker=10):
    # Mount Google Drive
    # Define the path to the Excel file
    #filename = 'validtickers_US_Others.xlsx'
    filename = 'validtickers_US_DOW_NASDAQ.xlsx'

    file_path = self.path + filename
    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path)

    # Assuming 'ticker' is the name of the column containing tickers
    if nTicker==0:
      ne=len(df)
    else:
      ne=nTicker
    self.US_OthersTickers = df['Ticker'].head(ne).tolist()
    self.US_OthersNames = df['Name'].head(ne).tolist()

  def getValidUS_ETF(self,nTicker=10):
    # Mount Google Drive
    # Define the path to the Excel file

    filename = 'validtickers_US_ETF.xlsx'
    file_path = self.path + filename
    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path)

    # Assuming 'ticker' is the name of the column containing tickers
    if nTicker==0:
      ne=len(df)
    else:
      ne=nTicker
    self.US_ETFTickers = df['Ticker'].head(ne).tolist()
    self.US_ETFNames = df['Name'].head(ne).tolist()

  def getValidTickerETF(self,nTicker=10):
    # Mount Google Drive
    # Define the path to the Excel file
    filename = 'validtickers_IT_ETF.xlsx'
    file_path = self.path + filename
    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path)

    # Assuming 'ticker' is the name of the column containing tickers
    if nTicker==0:
      ne=len(df)
    else:
      ne=nTicker
    self.ETFTickers = df['Ticker'].head(ne).tolist()
    self.ETFNames = df['Name'].head(ne).tolist()

  def getValidETC(self,nTicker=10):
    # Mount Google Drive
    # Define the path to the Excel file
    filename = 'validtickers_IT_ETC.xlsx'
    file_path = self.path + filename
    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path)

    # Assuming 'ticker' is the name of the column containing tickers
    if nTicker==0:
      ne=len(df)
    else:
      ne=nTicker
    self.ETCDf=df
    self.ETCTickers = df['Ticker'].head(ne).tolist()
    self.ETCNames = df['Name'].head(ne).tolist()

  def getValidMIB30(self,nTicker=10):
    # Mount Google Drive
    # Define the path to the Excel file
    filename = 'validtickers_IT_MIB30.xlsx' #validation not needed
    file_path = self.path + filename
    # Read the Excel file into a DataFrame
    df = pd.read_excel(file_path)

    # Assuming 'ticker' is the name of the column containing tickers
    if nTicker==0:
      ne=len(df)
    else:
      ne=nTicker
    self.MIB30Tickers = df['Ticker'].head(ne).tolist()
    self.MIB30Names = df['Name'].head(ne).tolist()

  def getValidDAX(self, nTicker=10):
    filename = 'validtickers_DE_DAX.xlsx'
    file_path = self.path + filename
    df = pd.read_excel(file_path)

    if nTicker == 0:
      ne = len(df)
    else:
      ne = nTicker
    self.DAXTickers = df['Ticker'].head(ne).tolist()
    self.DAXNames = df['Name'].head(ne).tolist()

  def getValidCrypto(self, nTicker=10):
    filename = 'validtickers_CRYPTO.xlsx'
    file_path = self.path + filename
    df = pd.read_excel(file_path)

    ne = len(df) if nTicker == 0 else nTicker
    self.CryptoTickers = df['Ticker'].head(ne).tolist()
    self.CryptoNames = df['Name'].head(ne).tolist()

  def dfToCSV(self, df, output_file):
    # Save DataFrame to a CSV file
    output_path = self.path + output_file
    df.to_csv(output_path, index=False)
    print(f"Output saved to: {output_path}")

  def fromCSVToDF(self, input_file):
        # Define the path to the CSV file
        input_path = self.path + input_file
        # Read the CSV file into a DataFrame
        df = pd.read_csv(input_path)
        return df

  def dfToXLSX(self, df, output_file):
    # Save DataFrame to a CSV file
    output_path = self.path + output_file
    df.to_excel(output_path, index=False)
    print(f"Output saved to: {output_path}")

  def fromXLSXToDF(self, input_file):
        # Define the path to the CSV file
        input_path = self.path + input_file
        # Read the CSV file into a DataFrame
        df = pd.read_excel(input_path)
        return df

  def getTickerList(self,market):
    if market=='ETC':
      return self.ETCTickers,self.ETCNames
    elif market=='MIB30':
      return self.MIB30Tickers,self.MIB30Names
    elif market=='ETF':
      return self.ETFTickers, self.ETFNames
    elif market=='US_ETF':
      return self.US_ETFTickers,self.US_ETFNames
    elif market=='US_Others':

      return self.US_OthersTickers,self.US_OthersNames
    elif market=='DAX':
      return self.DAXTickers, self.DAXNames
    elif market=='Crypto':
      return self.CryptoTickers, self.CryptoNames
    else:
      return None, None




#fh=fileHandling()
#ETC_Tickers=fh.ETCTickers
#ETC_names=fh.ETCNames
#ETC_df=fh.ETCDf
#print(ETC_Tickers)
#print(ETC_names)
#print(ETC_df.to_string())

#Preferite_Tickers=fh.US_ETFTickers
#Preferite_names=fh.US_ETFNames

#print(Preferite_Tickers)
#print(Preferite_names)
