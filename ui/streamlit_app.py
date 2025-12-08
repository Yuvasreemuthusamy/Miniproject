# ui/streamlit_app.py — Smart AI CFO (Enhanced UI)

import hashlib
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

# -------------------------
# Page Config
# -------------------------
st.set_page_config(page_title="Smart AI CFO", page_icon="💼", layout="wide")

# -------------------------
# Theme Engine (Light / Dark)
# -------------------------
mode = st.sidebar.selectbox("Theme", ["Dark (Pro)", "Light (Bright)"])

if mode == "Light (Bright)":
    BG = "#F8FAFC"
    TEXT = "#020617"
    MUTED = "#475569"
    CARD_BG = "#FFFFFF"
    PRIMARY = "#2563EB"
    ACCENT = "#7C3AED"
    SUCCESS = "#22C55E"
    DANGER = "#EF4444"
    CHART_THEME = "plotly_white"
else:  # Dark
    BG = "#020617"
    TEXT = "#E5E7EB"
    MUTED = "#9CA3AF"
    CARD_BG = "#0F172A"
    PRIMARY = "#3B82F6"
    ACCENT = "#A78BFA"
    SUCCESS = "#22C55E"
    DANGER = "#F87171"
    CHART_THEME = "plotly_dark"

CUSTOM_CSS = f"""
<style>
.stApp {{
    background: {BG};
    color: {TEXT};
}}
h1, h2, h3, h4, h5, h6, p, span, label, div {{
    color: {TEXT};
}}
section[data-testid='stSidebar'] {{
    background: linear-gradient(180deg,#020617,#020617);
}}
.metric {{
  padding:18px;
  border-radius:14px;
  background:{CARD_BG};
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  transition: transform .25s ease;
}}
.metric:hover {{ transform: translateY(-5px); }}
.metric-title {{ font-size:0.78rem; color:{MUTED}; letter-spacing:0.08em; text-transform:uppercase; }}
.metric-value {{ font-weight:800; font-size:1.7rem; margin-top:6px; color:{TEXT}; }}
.metric-sub {{ color:{MUTED}; font-size:0.85rem; margin-top:6px; }}
.insight {{
  padding:14px;
  border-radius:12px;
  background: linear-gradient(135deg,{SUCCESS},#A7F3D0);
  color:#020617;
  font-weight:600;
}}
.alert {{
  padding:12px;
  border-radius:10px;
  background:#3F0D12;
  color:#FFDADA;
  border-left:5px solid {DANGER};
}}
.stButton>button {{
  background: linear-gradient(90deg,{PRIMARY},{ACCENT});
  color:white;
  font-weight:700;
  border-radius:10px;
  padding:10px 18px;
  border:none;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------
# Helpers
# -------------------------


def compute_sha256(file_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(file_bytes)
    return h.hexdigest()


def fetch_json(endpoint: str, params=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params or {}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def download_csv(df: pd.DataFrame, name: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, name, "text/csv")


def build_overview_summary(
    trends_df: pd.DataFrame, vendors_df: pd.DataFrame, fc_df: pd.DataFrame
) -> str:
    if trends_df.empty:
        return "Upload at least two months of invoices to unlock Smart AI CFO insights."

    tdf = trends_df.copy()
    tdf["month"] = pd.to_datetime(tdf["month"], errors="coerce")
    tdf = tdf.dropna(subset=["month"]).sort_values("month")

    if len(tdf) < 2:
        last = tdf.iloc[-1]
        return (
            f"Initial spend data recorded for {last['month'].strftime('%b %Y')}. "
            "Once you have a second month, Smart AI CFO will start tracking month‑on‑month changes."
        )

    last = tdf.iloc[-1]
    prev = tdf.iloc[-2]
    delta = last["total_amount"] - prev["total_amount"]
    pct = delta / max(prev["total_amount"], 1) * 100
    direction = "higher" if delta >= 0 else "lower"

    msg = (
        f"Spending in {last['month'].strftime('%b %Y')} is "
        f"{abs(pct):.1f}% {direction} than the previous month."
    )

    if not vendors_df.empty and "total_amount" in vendors_df.columns:
        top_vendor = vendors_df.sort_values("total_amount", ascending=False).iloc[0]
        msg += (
            f" Top vendor is {top_vendor['vendor']} with "
            f"₹{top_vendor['total_amount']:,.0f} in total spend."
        )

    if not fc_df.empty and "yhat" in fc_df.columns:
        fc_sorted = fc_df.sort_values("ds")
        next_point = fc_sorted.iloc[0]
        msg += f" Next month is projected at around ₹{next_point['yhat']:,.0f}."

    return msg


# -------------------------
# Sidebar
# -------------------------
st.sidebar.markdown("# Smart AI CFO")
page = st.sidebar.radio(
    "Menu",
    [
        "Overview",
        "Invoices",
        "Vendors",
        "Analytics",
        "Forecasts",
        "Alerts",
        "Audit Trail",
    ],
)
st.sidebar.markdown("---")
st.sidebar.markdown("**Edition:** Prototype — Patent Candidate")

if st.sidebar.button("Show Onboarding Tips"):
    st.sidebar.info("1. Upload invoices\n2. Review analytics\n3. Export reports\n4. Use Forecasts")

# =========================
# OVERVIEW
# =========================
if page == "Overview":
    st.markdown("# Executive Dashboard")

    trends = fetch_json("/insights/expense-trends")
    vendors = fetch_json("/insights/top-vendors")
    forecast_payload = fetch_json("/forecast?periods=6")

    trends_df = pd.DataFrame(trends)
    vendors_df = pd.DataFrame(vendors)
    fc_df = (
        pd.DataFrame(forecast_payload.get("data", []))
        if isinstance(forecast_payload, dict)
        else pd.DataFrame()
    )

    col1, col2, col3 = st.columns(3)

    total = int(trends_df["total_amount"].sum()) if not trends_df.empty else 0
    months = trends_df["month"].nunique() if not trends_df.empty else 0
    vendor_count = len(vendors_df) if not vendors_df.empty else 0

    with col1:
        st.markdown(
            f"<div class='metric'><div class='metric-title'>Total Recorded</div>"
            f"<div class='metric-value'>₹{total:,}</div>"
            "<div class='metric-sub'>All invoices in system</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div class='metric'><div class='metric-title'>Active Months</div>"
            f"<div class='metric-value'>{months}</div>"
            "<div class='metric-sub'>Historical coverage</div></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div class='metric'><div class='metric-title'>Vendors</div>"
            f"<div class='metric-value'>{vendor_count}</div>"
            "<div class='metric-sub'>Suppliers monitored</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    summary_text = build_overview_summary(trends_df, vendors_df, fc_df)
    st.markdown(f"<div class='insight'>{summary_text}</div>", unsafe_allow_html=True)

    if not trends_df.empty:
        trends_df["month"] = pd.to_datetime(trends_df["month"], errors="coerce")
        trends_df = trends_df.dropna(subset=["month"]).sort_values("month")
        fig = px.line(
            trends_df,
            x="month",
            y="total_amount",
            markers=True,
            template=CHART_THEME,
            title="Total Spend Over Time",
        )
        fig.update_traces(line_color=PRIMARY)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Upload invoices to see your expense trajectory.")

# =========================
# INVOICES
# =========================
elif page == "Invoices":
    st.markdown("# Upload Invoice")
    uploaded = st.file_uploader(
        "Upload PNG/JPG/PDF", type=["png", "jpg", "jpeg", "pdf"]
    )

    if uploaded:
        file_bytes = uploaded.getvalue()
        sha = compute_sha256(file_bytes)
        st.success(f"SHA‑256 Provenance Hash: `{sha}`")

        if st.button("Upload & Process"):
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            r = requests.post(f"{API_BASE}/upload-invoice", files=files, timeout=60)
            if r.status_code == 200:
                parsed = r.json()
                st.json(parsed)
            else:
                st.error(f"Upload failed: {r.status_code} - {r.text}")

# =========================
# VENDORS
# =========================
elif page == "Vendors":
    st.markdown("# Vendor Intelligence")

    vdf = pd.DataFrame(fetch_json("/insights/top-vendors"))

    if vdf.empty:
        st.info("No vendor data available yet. Upload invoices to see vendor analytics.")
    else:
        col1, col2 = st.columns([2, 1])

        with col1:
            if {"vendor", "total_amount"} <= set(vdf.columns):
                fig = px.bar(
                    vdf.sort_values("total_amount", ascending=False).head(10),
                    x="vendor",
                    y="total_amount",
                    template=CHART_THEME,
                    title="Top 10 Vendors by Spend",
                )
                fig.update_traces(marker_color=PRIMARY)
                fig.update_layout(xaxis_title="", yaxis_title="Total Spend (₹)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Vendor data format is not as expected.")

        with col2:
            st.subheader("Vendor Details")
            selected_vendor = st.selectbox("Select vendor", vdf["vendor"].tolist())
            row = vdf[vdf["vendor"] == selected_vendor].iloc[0]

            st.write(f"**Total Spend:** ₹{row.get('total_amount', 0):,.0f}")

            inv_count = row.get("invoice_count", None)
            if inv_count is not None:
                st.write(f"**Invoices:** {int(inv_count)}")

            st.write(f"**Last Invoice:** {row.get('last_invoice_date', 'N/A')}")

            if st.button("Export Vendors CSV"):
                download_csv(vdf, "vendors.csv")

# =========================
# ANALYTICS
# =========================
elif page == "Analytics":
    st.markdown("# Detailed Expense Trends")

    df = pd.DataFrame(fetch_json("/insights/expense-trends"))
    if df.empty:
        st.info("No expense data available yet. Please upload invoices.")
    else:
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        df = df.dropna(subset=["month"]).sort_values("month")

        min_date, max_date = df["month"].min(), df["month"].max()
        start, end = st.slider(
            "Analysis window",
            min_value=min_date.to_pydatetime(),
            max_value=max_date.to_pydatetime(),
            value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
        )

        mask = (df["month"] >= start) & (df["month"] <= end)
        df_win = df[mask]

        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.area(
                df_win,
                x="month",
                y="total_amount",
                template=CHART_THEME,
                title="Monthly Spend (Selected Window)",
            )
            fig.update_traces(line_color=PRIMARY)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Data")
            st.dataframe(df_win, width="stretch", height=350)
            download_csv(df_win, "expense_trends_window.csv")

# =========================
# FORECASTS
# =========================
elif page == "Forecasts":
    st.markdown("# Cashflow Forecasts")

    months = st.slider("Forecast Months", 1, 12, 6)
    payload = fetch_json(f"/forecast?periods={months}")
    fc_df = (
        pd.DataFrame(payload.get("data", []))
        if isinstance(payload, dict)
        else pd.DataFrame()
    )

    if fc_df.empty:
        st.info(payload.get("message", "No forecast data available."))
    else:
        fc_df["ds"] = pd.to_datetime(fc_df["ds"], errors="coerce")
        fc_df = fc_df.dropna(subset=["ds"]).sort_values("ds")

        fig = px.line(
            fc_df,
            x="ds",
            y="yhat",
            template=CHART_THEME,
            title="Projected Monthly Spend",
            markers=True,
        )
        fig.update_traces(line_color=SUCCESS)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Forecast Table")
        st.dataframe(fc_df[["ds", "yhat"]], width="stretch", height=300)
        download_csv(fc_df, "forecast.csv")

# =========================
# ALERTS
# =========================
elif page == "Alerts":
    st.markdown("# Risk & Anomaly Alerts")

    dup = pd.DataFrame(fetch_json("/fraud/detect-duplicates"))
    anom = pd.DataFrame(fetch_json("/fraud/detect-anomalies"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Duplicate Invoices")
        if dup.empty:
            st.success("No duplicate invoices detected.")
        else:
            st.markdown(
                f"<div class='alert'>Found {len(dup)} potential duplicate invoices.</div>",
                unsafe_allow_html=True,
            )
            st.dataframe(dup, width="stretch", height=250)

    with col2:
        st.subheader("Amount Anomalies")
        if anom.empty:
            st.success("No amount anomalies detected.")
        else:
            st.markdown(
                f"<div class='alert'>Detected {len(anom)} invoices with abnormal amounts.</div>",
                unsafe_allow_html=True,
            )
            st.dataframe(anom, width="stretch", height=250)

# =========================
# AUDIT TRAIL
# =========================
elif page == "Audit Trail":
    st.markdown("# Audit Trail (Prototype)")
    adf = pd.DataFrame(fetch_json("/audit/list"))
    if adf.empty:
        st.info("No audit entries available (backend /audit endpoints optional).")
    else:
        st.dataframe(adf, width="stretch", height=400)
        download_csv(adf, "audit_trail.csv")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown(
    "<center><small>Smart AI CFO · Research Prototype · Team 099 · Patent Track</small></center>",
    unsafe_allow_html=True,
)
