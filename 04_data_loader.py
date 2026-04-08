'''
import pandas as pd
import numpy as np
df = pd.read_csv(r"d:\\Expense_Analyzer\\services\\Budget_Analysis.csv")

# Clean data
df = df.dropna()
df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
df = df.dropna()
print(df.columns)
'''