"""Data quality validation helpers for the warehouse ETL pipeline."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


REQUIRED_STAGING_COLUMNS = {
    "order_id",
    "order_date",
    "ship_date",
    "ship_mode",
    "customer_id",
    "customer_name",
    "segment",
    "country",
    "city",
    "state",
    "postal_code",
    "region",
    "product_id",
    "category",
    "sub_category",
    "product_name",
    "sales",
    "quantity",
    "discount",
    "profit",
}


def validate_staging_dataframe(df) -> None:
    """Validate the structure and key contents of the staging dataframe."""
    if isinstance(df, dict):
        df = pd.DataFrame(df)

    missing = sorted(REQUIRED_STAGING_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(
            "Missing required staging columns: " + ", ".join(missing)
        )

    if df.empty:
        raise ValueError("Staging dataframe is empty. No data was loaded.")

    required_non_null = [
        "order_id",
        "order_date",
        "customer_id",
        "product_id",
        "sales",
        "quantity",
        "profit",
        "state",
    ]

    null_cols = [
        col for col in required_non_null if df[col].isnull().any()
    ]
    if null_cols:
        raise ValueError(
            "Null values found in required staging columns: " + ", ".join(null_cols)
        )

    if not df["quantity"].ge(0).all():
        raise ValueError("Quantity values must be greater than or equal to zero.")

    if not df["sales"].ge(0).all():
        raise ValueError("Sales values must be greater than or equal to zero.")

    if not df["profit"].between(-1e9, 1e9).all():
        raise ValueError("Profit values contain invalid numbers.")

    if "row_id" in df.columns:
        duplicate_rows = df.duplicated(subset=["row_id"]).sum()
        if duplicate_rows:
            raise ValueError(
                f"Duplicate row identifiers detected in staging data: {duplicate_rows}"
            )
