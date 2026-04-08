import numpy as np

def calculate_stability_score(df, anomaly_count, prediction):
    df = df.copy()

    # Basic metrics
    total_transactions = len(df)
    anomaly_ratio = anomaly_count / total_transactions if total_transactions > 0 else 0

    # Volatility (standard deviation)
    volatility = df["amount"].std()
    avg_spending = df["amount"].mean()

    volatility_ratio = volatility / avg_spending if avg_spending != 0 else 0

    # Risk score components
    anomaly_penalty = anomaly_ratio * 40
    volatility_penalty = volatility_ratio * 30

    # Prediction growth penalty
    predicted_risk = (prediction / avg_spending) if avg_spending != 0 else 0
    prediction_penalty = predicted_risk * 20

    raw_score = 100 - (anomaly_penalty + volatility_penalty + prediction_penalty)

    final_score = max(0, min(100, round(raw_score, 2)))

    return final_score
