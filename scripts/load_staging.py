"""
ETL Staging Loader:
Loads Sample - Superstore.csv into the staging.stg_orders table.
"""

import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Ensure scripts directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_engine, get_connection
from quality_checks import validate_staging_dataframe


def load_staging_orders(csv_file: str | Path | None = None) -> int:
    """
    Extracts raw CSV data, performs minimal standardization, and loads into staging.stg_orders.
    Returns the number of rows currently in staging.stg_orders.
    """
    if csv_file is None:
        csv_file = Path(__file__).resolve().parent.parent / "data" / "Sample - Superstore.csv"
    else:
        csv_file = Path(csv_file)

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found at: {csv_file}")

    print(f"\n[EXTRACT] Reading CSV: {csv_file.name}...")
    df = pd.read_csv(csv_file, encoding="latin1", dtype={"Postal Code": str})
    print(f"  -> Rows read from file: {len(df):,}")

    validate_staging_dataframe(df.rename(columns={
        "Row ID": "row_id",
        "Order ID": "order_id",
        "Order Date": "order_date",
        "Ship Date": "ship_date",
        "Ship Mode": "ship_mode",
        "Customer ID": "customer_id",
        "Customer Name": "customer_name",
        "Segment": "segment",
        "Country": "country",
        "City": "city",
        "State": "state",
        "Postal Code": "postal_code",
        "Region": "region",
        "Product ID": "product_id",
        "Category": "category",
        "Sub-Category": "sub_category",
        "Product Name": "product_name",
        "Sales": "sales",
        "Quantity": "quantity",
        "Discount": "discount",
        "Profit": "profit",
    }))

    # Standardize column names to snake_case matching warehouse schema
    df = df.rename(
        columns={
            "Row ID": "row_id",
            "Order ID": "order_id",
            "Order Date": "order_date",
            "Ship Date": "ship_date",
            "Ship Mode": "ship_mode",
            "Customer ID": "customer_id",
            "Customer Name": "customer_name",
            "Segment": "segment",
            "Country": "country",
            "City": "city",
            "State": "state",
            "Postal Code": "postal_code",
            "Region": "region",
            "Product ID": "product_id",
            "Category": "category",
            "Sub-Category": "sub_category",
            "Product Name": "product_name",
            "Sales": "sales",
            "Quantity": "quantity",
            "Discount": "discount",
            "Profit": "profit",
        }
    )

    # Standardize datetime formats
    df["order_date"] = pd.to_datetime(df["order_date"], format="%m/%d/%Y")
    df["ship_date"] = pd.to_datetime(df["ship_date"], format="%m/%d/%Y")

    print("[TRANSFORM] Data types normalized and dates converted.")

    engine = get_engine()

    # Check if staging.stg_orders table exists
    with engine.connect() as conn:
        table_exists = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'staging' AND table_name = 'stg_orders'
                );
                """
            )
        ).scalar()

        if not table_exists:
            raise RuntimeError(
                "Table 'staging.stg_orders' does not exist! Please create tables first."
            )

    print("[LOAD] Truncating existing staging.stg_orders records...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging.stg_orders;"))

    print(f"[LOAD] Uploading {len(df):,} rows into staging.stg_orders...")
    df.to_sql(
        "stg_orders",
        engine,
        schema="staging",
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi",
    )

    with engine.connect() as conn:
        row_count = conn.execute(text("SELECT COUNT(*) FROM staging.stg_orders;")).scalar()

    print(f"[SUCCESS] Total rows verified in staging.stg_orders: {row_count:,}")
    return row_count


if __name__ == "__main__":
    load_staging_orders()