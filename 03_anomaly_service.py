import numpy as np

def detect_anomalies(df):
    mean = df["amount"].mean()
    std = df["amount"].std()

    df["z_score"] = (df["amount"] - mean) / std
    df["anomaly"] = np.where(abs(df["z_score"]) > 2, 1, 0)

    anomaly_count = df["anomaly"].sum()

    return anomaly_count
