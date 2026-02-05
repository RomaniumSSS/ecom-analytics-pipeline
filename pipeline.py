"""ETL pipeline: load raw orders → clean → calculate KPIs → export JSON."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"


# ── Extract ──────────────────────────────────────────────────────────────────


def load_orders(path: Path) -> pd.DataFrame:
    """Load raw CSV into a DataFrame."""
    df = pd.read_csv(path, dtype={"customer_id": str, "customer_email": str})
    print(f"  Loaded {len(df):,} rows")
    return df


# ── Transform: Cleaning ──────────────────────────────────────────────────────


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw order data: fix types, remove bad rows, deduplicate."""
    initial = len(df)

    # Parse dates (handle mixed formats)
    df["order_date"] = pd.to_datetime(df["order_date"], format="mixed", dayfirst=False)

    # Remove rows with negative or zero quantity
    df = df[df["quantity"] > 0].copy()

    # Remove exact duplicate rows
    df = df.drop_duplicates()

    # Fill missing emails with placeholder
    df["customer_email"] = df["customer_email"].replace("", np.nan)
    df["customer_email"] = df["customer_email"].fillna("unknown@placeholder.com")

    # Ensure numeric types
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["discount"] = pd.to_numeric(df["discount"], errors="coerce").fillna(0.0)
    df["shipping_cost"] = pd.to_numeric(df["shipping_cost"], errors="coerce").fillna(
        0.0
    )

    # Drop rows where unit_price couldn't be parsed
    df = df.dropna(subset=["unit_price"])

    # Calculate derived columns
    df["line_total"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])
    df["order_month"] = df["order_date"].dt.to_period("M")
    df["order_week"] = df["order_date"].dt.to_period("W")

    removed = initial - len(df)
    print(f"  Cleaned: removed {removed:,} bad/duplicate rows, {len(df):,} remaining")
    return df


# ── Transform: KPI Calculation ───────────────────────────────────────────────


def calculate_kpis(df: pd.DataFrame) -> dict:
    """Calculate top-level KPI metrics."""
    completed = df[df["order_status"] == "completed"]
    refunded = df[df["order_status"] == "refunded"]

    total_revenue = completed["line_total"].sum()
    total_orders = completed["order_id"].nunique()
    aov = total_revenue / total_orders if total_orders > 0 else 0

    total_all_orders = df["order_id"].nunique()
    refund_count = refunded["order_id"].nunique()
    refund_rate = refund_count / total_all_orders if total_all_orders > 0 else 0

    # Month-over-month delta for KPI cards
    monthly_rev = completed.groupby("order_month")["line_total"].sum().sort_index()
    if len(monthly_rev) >= 2:
        last_month_rev = monthly_rev.iloc[-1]
        prev_month_rev = monthly_rev.iloc[-2]
        rev_delta = (
            (last_month_rev - prev_month_rev) / prev_month_rev if prev_month_rev else 0
        )
    else:
        rev_delta = 0

    monthly_orders = completed.groupby("order_month")["order_id"].nunique().sort_index()
    if len(monthly_orders) >= 2:
        prev_orders = monthly_orders.iloc[-2]
        orders_delta = (
            (monthly_orders.iloc[-1] - prev_orders) / prev_orders if prev_orders else 0
        )
    else:
        orders_delta = 0

    monthly_aov = monthly_rev / monthly_orders
    if len(monthly_aov) >= 2:
        prev_aov = monthly_aov.iloc[-2]
        aov_delta = (monthly_aov.iloc[-1] - prev_aov) / prev_aov if prev_aov else 0
    else:
        aov_delta = 0

    kpis = {
        "total_revenue": round(total_revenue, 2),
        "total_orders": int(total_orders),
        "aov": round(aov, 2),
        "refund_rate": round(refund_rate, 4),
        "rev_delta": round(rev_delta, 4),
        "orders_delta": round(orders_delta, 4),
        "aov_delta": round(aov_delta, 4),
    }
    return kpis


def aggregate_monthly_revenue(df: pd.DataFrame) -> list[dict]:
    """Monthly revenue trend for completed orders."""
    completed = df[df["order_status"] == "completed"]
    monthly = (
        completed.groupby("order_month")["line_total"].sum().sort_index().reset_index()
    )
    monthly.columns = ["month", "revenue"]
    monthly["month"] = monthly["month"].astype(str)
    return monthly.to_dict(orient="records")


def aggregate_by_category(df: pd.DataFrame) -> list[dict]:
    """Revenue breakdown by product category."""
    completed = df[df["order_status"] == "completed"]
    cat = (
        completed.groupby("product_category")["line_total"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    cat.columns = ["category", "revenue"]
    return cat.to_dict(orient="records")


def top_products(df: pd.DataFrame, n: int = 10) -> list[dict]:
    """Top N products by revenue."""
    completed = df[df["order_status"] == "completed"]
    top = (
        completed.groupby("product_name")["line_total"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .reset_index()
    )
    top.columns = ["product", "revenue"]
    return top.to_dict(orient="records")


def aggregate_by_country(df: pd.DataFrame) -> list[dict]:
    """Revenue by shipping country."""
    completed = df[df["order_status"] == "completed"]
    geo = (
        completed.groupby("shipping_country")["line_total"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    geo.columns = ["country", "revenue"]
    return geo.to_dict(orient="records")


def customer_cohorts(df: pd.DataFrame) -> list[dict]:
    """New vs returning customers by month."""
    completed = df[df["order_status"] == "completed"].copy()

    # First purchase month per customer
    first_purchase = (
        completed.groupby("customer_id")["order_date"]
        .min()
        .dt.to_period("M")
        .rename("first_month")
    )
    completed = completed.merge(first_purchase, on="customer_id", how="left")
    completed["is_new"] = completed["order_month"] == completed["first_month"]

    monthly_cohort = (
        completed.groupby(["order_month", "is_new"])["customer_id"]
        .nunique()
        .unstack(fill_value=0)
        .sort_index()
        .reset_index()
    )
    monthly_cohort.columns = ["month", "returning", "new"]
    monthly_cohort["month"] = monthly_cohort["month"].astype(str)
    return monthly_cohort.to_dict(orient="records")


# ── Load: Export ─────────────────────────────────────────────────────────────


def export_metrics(metrics: dict, output_path: Path) -> None:
    """Write metrics dict as JSON for the dashboard."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  Exported metrics to {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────


def run_pipeline() -> dict:
    """Execute the full ETL pipeline and return metrics dict."""
    csv_path = DATA_DIR / "raw_orders.csv"
    json_path = OUTPUT_DIR / "metrics.json"

    print("=== E-commerce Analytics Pipeline ===\n")

    print("[1/4] Loading data...")
    df = load_orders(csv_path)

    print("[2/4] Cleaning data...")
    df = clean(df)

    print("[3/4] Calculating KPIs...")
    kpis = calculate_kpis(df)

    print("\n  --- Summary ---")
    print(f"  Total Revenue:  ${kpis['total_revenue']:,.2f}")
    print(f"  Total Orders:   {kpis['total_orders']:,}")
    print(f"  Avg Order Value: ${kpis['aov']:.2f}")
    print(f"  Refund Rate:    {kpis['refund_rate']:.1%}")

    metrics = {
        "kpis": kpis,
        "monthly_revenue": aggregate_monthly_revenue(df),
        "by_category": aggregate_by_category(df),
        "top_products": top_products(df),
        "by_country": aggregate_by_country(df),
        "customer_cohorts": customer_cohorts(df),
        "data_period": {
            "start": df["order_date"].min().strftime("%Y-%m-%d"),
            "end": df["order_date"].max().strftime("%Y-%m-%d"),
        },
    }

    print("\n[4/4] Exporting metrics...")
    export_metrics(metrics, json_path)

    print("\nPipeline complete.")
    return metrics


if __name__ == "__main__":
    run_pipeline()
