import pandas as pd
try:
    df = pd.read_excel('analyses/MIB30_TA_Analyses.xlsx')
    print("Columns:", df.columns.tolist())
    if 'Date' in df.columns:
        print("First few dates:", df['Date'].head().tolist())
    else:
        print("No 'Date' column found.")
except Exception as e:
    print("Error:", e)
