'''
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile, Form
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import pandas as pd
import os
import json

from database import engine, SessionLocal
from database import Base
from services.models import User, Expense, Activity
from services.anomaly_service import detect_anomalies
from services.model_service import predict_next_month
from services.recommendation_service import generate_recommendation

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# DATABASE DEPENDENCY
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# ================= REGISTER =================
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request,})
@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return HTMLResponse("Username already exists")

        hashed = pwd_context.hash(password[:72])
        user = User(username=username, password=hashed)
        db.add(user)
        db.commit()

        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        return HTMLResponse(f"Register Error: {str(e)}")
# ================= LOGIN =================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()

        if not user or not pwd_context.verify(password[:72], user.password):
            return HTMLResponse("Invalid Username or Password")

        response = RedirectResponse("/", status_code=303)
        response.set_cookie("user", user.username)
        return response

    except Exception as e:
        return HTMLResponse(f"Login Error: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    context = {
        "request": request,
        "username": "User",  # you can later replace with session user
        "total_expense": 0,
        "monthly_summary": []
    }
    return templates.TemplateResponse("index.html", context)
@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("user")
    return response
# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    username = request.cookies.get("user")
    if not username:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("index.html", {
    "request": request,
    "username": username,
    "total": 0,
    "average": 0,
    "prediction": 0,
    "anomaly_count": 0,
    "recommendation": "",
    "category_summary": json.dumps({}),
    "monthly_labels": json.dumps([]),
    "monthly_values": json.dumps([])
})
# ================= UPLOAD =================
@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        username = request.cookies.get("user")
        if not username:
            return RedirectResponse("/login", status_code=303)

        user = db.query(User).filter(User.username == username).first()
        if not user:
            return HTMLResponse("User not found")

        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Read CSV
        df = pd.read_csv(file_path)

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower()

        required_columns = {"date", "category", "amount"}
        if not required_columns.issubset(df.columns):
            return HTMLResponse("CSV must contain: date, category, amount columns")

        # Convert types safely
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df.dropna(subset=["date", "category", "amount"], inplace=True)
        # category_summary = df.groupby("category")["amount"].sum().to_dict()
        category_data = df.groupby("category")["amount"].sum().sort_values(ascending=False)

        top_categories = category_data.head(4)
        others_sum = category_data.iloc[4:].sum()

        labels = list(top_categories.index)
        values = list(top_categories.values)

        if others_sum > 0:
            labels.append("Others")
            values.append(float(others_sum))

        all_categories = category_data.to_dict()
        monthly_summary = df.groupby(df["date"].dt.to_period("M"))["amount"].sum().reset_index()
        monthly_summary["date"] = monthly_summary["date"].astype(str)
        # labels = list(category_summary.keys())
        # values = list(category_summary.values())

        if df.empty:
            return HTMLResponse("CSV has no valid data after cleaning.")

        # Save expenses
        for _, row in df.iterrows():
            expense = Expense(
                date=row["date"].to_pydatetime().replace(tzinfo=None),
                category=row["category"],
                amount=float(row["amount"]),
                user_id=user.id
)
            db.add(expense)

        db.commit()

        # Log activity
        db.add(Activity(action="Uploaded expense file", user_id=user.id))
        db.commit()

        # Safe service execution
        try:
            anomaly_count = detect_anomalies(df)
        except:
            anomaly_count = 0

        try:
            prediction = predict_next_month(df)
        except:
            prediction = 0

        try:
            recommendation = generate_recommendation(df)
        except:
            recommendation = "No recommendation available"

        total = df["amount"].sum()
        average = df["amount"].mean()

        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "labels": labels,
            "values": values,
            "username": username,
            "total": round(total, 2),
            "average": round(average, 2),
            "prediction": prediction,
            "anomaly_count": anomaly_count,
            "recommendation": recommendation,
            "category_data": json.dumps(category_data),
            "all_categories": json.dumps(all_categories),
            "monthly_labels": json.dumps(monthly_summary["date"].tolist()),
            "monthly_values": json.dumps(monthly_summary["amount"].tolist())

        })

    except Exception as e:
        return HTMLResponse(f"Upload Error: {str(e)}")
'''

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import pandas as pd
import os
import json

from database import engine, SessionLocal
from database import Base
from services.models import User, Expense, Activity
from services.anomaly_service import detect_anomalies
from services.model_service import predict_next_month
from services.recommendation_service import generate_recommendation

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================= DATABASE DEPENDENCY =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================= REGISTER =================
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return HTMLResponse("Username already exists")

    hashed = pwd_context.hash(password[:72])
    user = User(username=username, password=hashed)
    db.add(user)
    db.commit()

    return RedirectResponse("/login", status_code=303)


# ================= LOGIN =================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()

    if not user or not pwd_context.verify(password[:72], user.password):
        return HTMLResponse("Invalid Username or Password")

    response = RedirectResponse("/", status_code=303)
    response.set_cookie("user", user.username)
    return response


# ================= LOGOUT =================
@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("user")
    return response


# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    username = request.cookies.get("user")
    if not username:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "total": 0,
        "average": 0,
        "prediction": 0,
        "anomaly_count": 0,
        "recommendation": "",
        "labels": json.dumps([]),
        "values": json.dumps([]),
        "all_categories": json.dumps({}),
        "monthly_labels": json.dumps([]),
        "monthly_values": json.dumps([])
    })
# ================= UPLOAD =================
@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    username = request.cookies.get("user")
    if not username:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.username == username).first()
    if not user:
        return HTMLResponse("User not found")

    # Save file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip().str.lower()

    required_columns = {"date", "category", "amount"}
    if not required_columns.issubset(df.columns):
        return HTMLResponse("CSV must contain: date, category, amount")
    
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date", "category", "amount"], inplace=True)
    
    if df.empty:
        return HTMLResponse("CSV has no valid data after cleaning.")

    # ================= CATEGORY LOGIC =================
    category_data = df.groupby("category")["amount"].sum().sort_values(ascending=False)

    top_categories = category_data.head(4)
    others_sum = category_data.iloc[4:].sum()

    labels = list(top_categories.index)
    values = list(top_categories.values)

    if others_sum > 0:
        labels.append("Others")
        values.append(float(others_sum))

    all_categories = category_data.to_dict()

    # ================= MONTHLY =================
    monthly_summary = df.groupby(df["date"].dt.to_period("M"))["amount"].sum().reset_index()
    monthly_summary["date"] = monthly_summary["date"].astype(str)
    from datetime import datetime

# ================= CURRENT MONTH PREDICTION =================

    today = datetime.now()

    current_month_data = df[
        (df["date"].dt.month == today.month) &
        (df["date"].dt.year == today.year)
    ]

    if not current_month_data.empty:
        days_passed = today.day
        total_so_far = current_month_data["amount"].sum()
        current_month_prediction = (total_so_far / days_passed) * 30
    else:
        current_month_prediction = 0
    # ================= SAVE TO DB =================
    for _, row in df.iterrows():
        expense = Expense(
            date=row["date"].to_pydatetime().replace(tzinfo=None),
            category=row["category"],
            amount=float(row["amount"]),
            user_id=user.id
        )
        db.add(expense)

    db.commit()

    db.add(Activity(action="Uploaded expense file", user_id=user.id))
    db.commit()

    # ================= SERVICES =================
    anomaly_count = detect_anomalies(df)
    prediction = predict_next_month(df)
    recommendation = generate_recommendation(df)
    
    total = df["amount"].sum()
    average = df["amount"].mean()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "total": round(total, 2),
        "average": round(average, 2),
        "prediction": prediction,
        "anomaly_count": anomaly_count,
        "recommendation": recommendation,
        "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
        "amounts": df["amount"].tolist(),
        "labels": labels,
        "values": values,
        "current_month_prediction": round(current_month_prediction, 2),
        "all_categories": all_categories,
        "monthly_labels": monthly_summary["date"].tolist(),
        "monthly_values": monthly_summary["amount"].tolist()
    })