from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd

def predict_next_month(df):

    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M")

    monthly = df.groupby("year_month")["amount"].sum().reset_index()
    monthly["month_index"] = np.arange(len(monthly))

    if len(monthly) < 2:
        return round(monthly["amount"].mean(), 2)

    X = monthly[["month_index"]]
    y = monthly["amount"]

    model = LinearRegression()
    model.fit(X, y)

    next_month = [[len(monthly)]]
    prediction = model.predict(next_month)[0]

    return round(prediction, 2)
