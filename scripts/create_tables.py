"""
Warehouse Setup and Verification Script.

- Checks existing tables in 'staging' and 'dw' schemas.
- Creates any missing tables and indexes using sql/01_create_warehouse.sql.
- Displays a clear status summary (table name, column count, row count).
"""

import sys
from pathlib import Path
from sqlalchemy import text

# Ensure scripts directory is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_engine, get_connection

EXPECTED_TABLES = [
    ("staging", "stg_orders"),
    ("staging", "stg_holidays"),
    ("staging", "stg_stores"),
    ("staging", "stg_promotions"),
    ("dw", "dim_date"),
    ("dw", "dim_product"),
    ("dw", "dim_customer"),
    ("dw", "dim_store"),
    ("dw", "dim_promo"),
    ("dw", "dim_ship_mode"),
    ("dw", "fact_sales"),
]


def get_existing_tables():
    """Returns a dict of {(schema, table): column_count} for staging and dw schemas."""
    engine = get_engine()
    query = text(
        """
        SELECT table_schema, table_name, count(column_name) AS col_count
        FROM information_schema.columns
        WHERE table_schema IN ('staging', 'dw')
        GROUP BY table_schema, table_name;
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        return {(row[0], row[1]): row[2] for row in rows}


def get_table_row_count(schema: str, table: str) -> int:
    """Returns the current row count for a given table."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}";')).scalar()
            return count or 0
    except Exception:
        return 0


def print_table_status():
    """Prints a formatted report of all expected warehouse tables."""
    existing = get_existing_tables()
    
    print("\n" + "=" * 70)
    print(f"{'Schema.Table':<28} | {'Status':<12} | {'Columns':<8} | {'Rows':<8}")
    print("-" * 70)
    
    all_present = True
    for schema, table in EXPECTED_TABLES:
        full_name = f"{schema}.{table}"
        if (schema, table) in existing:
            cols = existing[(schema, table)]
            rows = get_table_row_count(schema, table)
            print(f"{full_name:<28} | {'EXISTS':<12} | {cols:<8} | {rows:<8}")
        else:
            all_present = False
            print(f"{full_name:<28} | {'MISSING':<12} | {'-':<8} | {'-':<8}")
            
    print("=" * 70)
    return all_present


def setup_warehouse(force: bool = False):
    """
    Checks table status and applies sql/01_create_warehouse.sql if needed.
    """
    print("Checking current warehouse table status...")
    existing = get_existing_tables()
    missing = [(s, t) for (s, t) in EXPECTED_TABLES if (s, t) not in existing]

    if not missing and not force:
        print(f"[INFO] All {len(EXPECTED_TABLES)} expected tables already exist in the database.")
        print_table_status()
        print("\nNo setup action needed. Warehouse is fully initialized!")
        return

    if missing:
        print(f"[INFO] Found {len(missing)} missing table(s): {[f'{s}.{t}' for s, t in missing]}")

    sql_path = Path(__file__).resolve().parent.parent / "sql" / "01_create_warehouse.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"Cannot find SQL file: {sql_path}")

    print(f"Applying schema & table creation from: {sql_path.name}...")
    sql_content = sql_path.read_text(encoding="utf-8")
    
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql_content))
    
    print("[SUCCESS] SQL script executed successfully.")
    print("\nUpdated Warehouse Status:")
    print_table_status()


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    setup_warehouse(force=force_run)