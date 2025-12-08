# insights/analytics.py

import pandas as pd


def expense_trends(data):
    """
    data: list of dicts like
        {
            "invoice_date": <date or string>,
            "vendor": <str>,
            "category": <str>,
            "amount": <float>
        }

    Returns a DataFrame with columns:
        - month         (string, 'YYYY-MM')
        - total_amount  (float)
    """

    df = pd.DataFrame(data)

    if df.empty:
        return pd.DataFrame(columns=["month", "total_amount"])

    # Parse dates; invalid values -> NaT
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df = df.dropna(subset=["invoice_date"])

    if df.empty:
        return pd.DataFrame(columns=["month", "total_amount"])

    # Month as string, e.g. '2025-11'
    df["month"] = df["invoice_date"].dt.to_period("M").astype(str)

    trends = (
        df.groupby("month")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total_amount"})
    )

    return trends


def top_vendors(data, n: int = 5):
    """
    Optional helper:

    Returns top-N vendors by total spend with columns:
        - vendor
        - total_amount
    """

    df = pd.DataFrame(data)

    if df.empty:
        return pd.DataFrame(columns=["vendor", "total_amount"])

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["amount"])

    if df.empty:
        return pd.DataFrame(columns=["vendor", "total_amount"])

    vendors = (
        df.groupby("vendor")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total_amount"})
        .sort_values("total_amount", ascending=False)
        .head(n)
    )

    return vendors
