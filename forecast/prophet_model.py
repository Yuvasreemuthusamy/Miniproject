# forecast/prophet_model.py

import pandas as pd
from prophet import Prophet


def prepare_data_for_prophet(invoices):
    """
    invoices: list of dicts like
        {"invoice_date": <date or string>, "amount": <float>}
    Returns a dataframe with Prophet-ready columns ds (date) and y (value).
    """

    df = pd.DataFrame(invoices)

    if df.empty:
        return df

    # Parse dates; invalid ones become NaT
    df["ds"] = pd.to_datetime(df["invoice_date"], errors="coerce")

    # Amounts as float
    df["y"] = pd.to_numeric(df["amount"], errors="coerce")

    # Keep only the columns we care about, sorted by date
    df = df[["ds", "y"]].sort_values("ds")

    # Drop rows where date or amount is missing
    df = df.dropna(subset=["ds", "y"])

    return df


def run_prophet_forecast(invoices, periods: int = 6):
    """
    Build and run a Prophet model.
    Returns:
        - pandas DataFrame with columns [ds, yhat, yhat_lower, yhat_upper]
        - or None if there is not enough valid data.
    """

    df = prepare_data_for_prophet(invoices)

    # Prophet needs at least 2 data points
    if df is None or df.shape[0] < 2:
        return None

    # Basic Prophet model with monthly seasonality
    m = Prophet()
    m.add_seasonality(name="monthly", period=30.5, fourier_order=5)
    m.fit(df)

    # Create future dates (monthly)
    future = m.make_future_dataframe(periods=periods, freq="M")

    # Forecast
    forecast = m.predict(future)

    # Keep only the last N periods for the API
    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)

    return result
