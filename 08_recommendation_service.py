'''
def predict_next_month(df):
    monthly_avg = df["amount"].mean()
    prediction = monthly_avg * 30   # assuming daily entries
    return round(prediction, 2)
def generate_recommendation(df):
    category_sum = df.groupby("category")["amount"].sum()
    highest_category = category_sum.idxmax()

    return f"You are spending most on {highest_category}. Consider reducing it." '''
def generate_recommendation(df):
    category_sum = df.groupby("category")["amount"].sum()
    highest_category = category_sum.idxmax()

    return f"You are spending most on {highest_category}. Try reducing this category."