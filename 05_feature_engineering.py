import pandas as pd
import numpy as np

def create_date_features(df: pd.DataFrame):

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    df["year_month"] = df["date"].dt.to_period("M")
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.month_name()
    df["day"] = df["date"].dt.day
    df["day_name"] = df["date"].dt.day_name()
    df["weekday"] = df["date"].dt.weekday

    return df


def create_advanced_features(df: pd.DataFrame):

    df["log_amount"] = np.log1p(df["amount"])

    threshold = df["amount"].mean() + df["amount"].std()
    df["high_expense_flag"] = (df["amount"] > threshold).astype(int)

    monthly = df.groupby("year_month")["amount"].agg(
        monthly_total="sum",
        monthly_avg="mean",
        monthly_max="max"
    ).reset_index()

    df = df.merge(monthly, on="year_month", how="left")

    return df
