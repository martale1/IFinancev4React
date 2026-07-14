import pandas as pd
excel_path = "analyses/DAX_TA_Analyses.xlsx"
df = pd.read_excel(excel_path, sheet_name="Sheet1")
print("All columns:")
print(list(df.columns))
