import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import shutil, os
from db.db_utils import SessionLocal, engine
from db.models import Base, Vendor, Invoice
from ocr.invoice_ocr import ocr_image, ocr_pdf, extract_invoice_fields
from insights.analytics import expense_trends as expense_trends_func, top_vendors as top_vendors_func
from fraud.detect import detect_duplicates, detect_amount_anomalies
from forecast.prophet_model import run_prophet_forecast
from datetime import datetime

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Smart AI CFO API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- Upload invoice ----------------

@app.post("/upload-invoice")
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    upload_dir = "temp_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # OCR
    if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raw_text = ocr_image(file_path)
    elif file.filename.lower().endswith(".pdf"):
        raw_text = ocr_pdf(file_path)
    else:
        raise HTTPException(status_code=400, detail="Invalid file format")

    fields = extract_invoice_fields(raw_text)

    vendor_name = fields.get("vendor") or "Unknown Vendor"
    vendor = db.query(Vendor).filter(Vendor.name == vendor_name).first()
    if not vendor:
        vendor = Vendor(name=vendor_name)
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

    # Extract and convert date string to datetime.date
    raw_date = fields.get("invoice_date") or fields.get("date")
    date_obj = None
    if raw_date:
        try:
            # Adjust format as per your OCR output, here it's MM/DD/YYYY
            date_obj = datetime.strptime(raw_date, "%m/%d/%Y").date()
        except Exception as e:
            print(f"Date parsing error: {e}")
            date_obj = None

    invoice = Invoice(
        vendor_id=vendor.id,
        invoice_no=fields.get("invoice_no") or "N/A",
        invoice_date=date_obj,
        amount=fields.get("amount") or 0.0,
        currency=fields.get("currency") or "N/A",
        line_items=[],
        confidence=0.9,
        parsed_at=None,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    os.remove(file_path)

    return JSONResponse(
        content={
            "message": "Invoice uploaded and processed successfully",
            "invoice_id": invoice.id,
            "parsed_fields": fields,
        }
    )


# ---------------- Insights: expense trends ----------------

@app.get("/insights/expense-trends")
def expense_trends_endpoint(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()
    data = [
        {
            "invoice_date": inv.invoice_date,
            "vendor": inv.vendor.name if inv.vendor else "Unknown",
            "category": "General",
            "amount": inv.amount,
        }
        for inv in invoices
    ]

    df = pd.DataFrame(data)
    if df.empty:
        return []

    # Use same cleaning logic as insights.analytics.expense_trends
    trends_df = expense_trends_func(data)
    if trends_df is None or trends_df.empty:
        return []

    return trends_df.to_dict(orient="records")


# ---------------- Insights: top vendors ----------------

@app.get("/insights/top-vendors")
def top_vendors_endpoint(db: Session = Depends(get_db), limit: int = 10):
    invoices = db.query(Invoice).all()
    data = [
        {
            "invoice_date": inv.invoice_date,
            "vendor": inv.vendor.name if inv.vendor else "Unknown",
            "category": "General",
            "amount": inv.amount,
        }
        for inv in invoices
    ]

    df = pd.DataFrame(data)
    if df.empty:
        return []

    # Reuse your analytics helper, which already cleans numbers
    vendors_df = top_vendors_func(data, n=limit)
    if vendors_df is None or vendors_df.empty:
        return []

    # If last_invoice_date exists and is datetime-like, stringify it
    if "last_invoice_date" in vendors_df.columns:
        vendors_df["last_invoice_date"] = vendors_df["last_invoice_date"].astype(str)

    return vendors_df.to_dict(orient="records")


# ---------------- Fraud detection ----------------

@app.get("/fraud/detect-duplicates")
def detect_duplicates_endpoint(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()
    data = [
        {
            "vendor": inv.vendor.name if inv.vendor else "Unknown",
            "invoice_no": inv.invoice_no,
            "amount": inv.amount,
        }
        for inv in invoices
    ]
    duplicates_df = detect_duplicates(data)
    return duplicates_df.to_dict(orient="records")


@app.get("/fraud/detect-anomalies")
def detect_anomalies_endpoint(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()
    data = [{"amount": inv.amount} for inv in invoices]
    anomalies_df = detect_amount_anomalies(data)
    return anomalies_df.to_dict(orient="records")


# ---------------- Forecasting ----------------

@app.get("/forecast")
def forecast_expenses(periods: int = 6, db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()

    # Build raw data for Prophet
    data = [
        {"invoice_date": inv.invoice_date, "amount": inv.amount}
        for inv in invoices
    ]

    # If there is no data at all, return a friendly message
    if not data:
        return {
            "message": "No invoices available for forecasting.",
            "data": [],
        }

    # Call Prophet wrapper (should drop NaNs and return None if < 2 rows)
    forecast_df = run_prophet_forecast(data, periods)

    if forecast_df is None:
        # Not enough valid rows (e.g., all dates null or only 1 row)
        return {
            "message": "Need at least 2 invoices with valid dates and amounts for forecasting.",
            "data": [],
        }

    # Convert Timestamp to ISO strings for JSON
    forecast_df = forecast_df.copy()
    if "ds" in forecast_df.columns:
        forecast_df["ds"] = forecast_df["ds"].dt.strftime("%Y-%m-%d")

    result = forecast_df.to_dict(orient="records")
    return JSONResponse(content={"message": "OK", "data": result})
