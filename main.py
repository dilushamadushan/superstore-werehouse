"""
Superstore Data Warehouse Management Console (CLI).

Main entry point for managing database connection, schema setup, staging ETL,
reference data ingestion, dimensional star-schema build, analytics queries,
report generation, and data cleanup.
"""

import sys
import os
import time
import io
from pathlib import Path

# Force UTF-8 output on Windows to prevent garbled box-drawing/arrow characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure root directory and scripts directory are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.db import (
    test_connection_health,
    truncate_all_warehouse_tables,
    drop_warehouse_schemas,
    get_db_url,
)
from scripts.create_tables    import print_table_status, setup_warehouse
from scripts.load_staging     import load_staging_orders
from scripts.load_reference_data import load_reference_data
from scripts.build_warehouse  import build_warehouse
from scripts.run_queries      import run_queries, list_available_queries
from scripts.generate_report  import generate_reports


# ─────────────────────────────────────────────────────────────────────────────
def print_header(title: str):
    width = 78
    print("\n" + "=" * width)
    print(f"  {title.upper()}")
    print("=" * width)


def print_menu():
    print("\n" + "+" + "─" * 76 + "+")
    print("|" + "      SUPERSTORE DATA WAREHOUSE MANAGER".center(76) + "|")
    print("|" + "  Advanced Star Schema  |  25 BI Queries  |  Excel & HTML Reports".center(76) + "|")
    print("+" + "─" * 76 + "+")
    entries = [
        ("1",  "Check Database Connection & Table Status"),
        ("2",  "Create Warehouse Schemas & Tables (staging & dw)"),
        ("3",  "Load Staging Orders (Superstore CSV → staging.stg_orders)"),
        ("4",  "Load Reference Data (Holidays API, Stores, Promotions)"),
        ("5",  "Build Data Warehouse (Advanced Star Schema)"),
        ("6",  "Run Analytics Queries (25 Business Intelligence Questions)"),
        ("7",  "Generate Reports (Excel workbook + HTML report)"),
        ("8",  "Truncate / Delete All Table Data (keep table structures)"),
        ("9",  "Clean Reset: Drop Schemas from Supabase (DROP staging, dw)"),
        ("0",  "Exit"),
    ]
    for num, label in entries:
        line = f"  {num:>2}. {label}"
        print("|" + line.ljust(76) + "|")
    print("+" + "─" * 76 + "+")


# ─────────────────────────────────────────────────────────────────────────────
def handle_check_db():
    print_header("1. Checking Database & Warehouse Status")
    print("Testing connection to Supabase...")
    start = time.time()
    ok, msg = test_connection_health()
    elapsed = (time.time() - start) * 1000

    if not ok:
        print(f"\n[ERROR] Connection failed: {msg}")
        return

    print(f"[SUCCESS] Connected in {elapsed:.1f} ms")
    print(f"Database Server: {msg[:70]}...")

    url  = get_db_url()
    host = url.split("@")[-1].split("/")[0] if "@" in url else "configured host"
    print(f"Host:            {host}")

    print("\nChecking warehouse tables:")
    print_table_status()


def handle_create_tables():
    print_header("2. Setting up Warehouse Schemas & Tables")
    setup_warehouse(force=False)


def handle_load_staging():
    print_header("3. Loading CSV Data into Staging")
    try:
        rows = load_staging_orders()
        print(f"\n[COMPLETE] Successfully populated staging.stg_orders with {rows:,} rows.")
    except Exception as e:
        print(f"\n[ERROR] Failed to load staging orders: {e}")


def handle_load_reference():
    print_header("4. Loading Reference Data")
    try:
        load_reference_data()
        print("\n[COMPLETE] All reference tables populated successfully.")
    except Exception as e:
        print(f"\n[ERROR] Failed to load reference data: {e}")


def handle_build_warehouse():
    print_header("5. Building Data Warehouse (Advanced Star Schema)")
    try:
        build_warehouse()
        print("\n[COMPLETE] Warehouse build and validation completed successfully!")
    except Exception as e:
        print(f"\n[ERROR] Warehouse build failed: {e}")


def parse_query_selection(choice: str) -> set[str] | None:
    """Parses user input into a set of query IDs like {'Q1', 'Q4'}, handling numbers and ranges."""
    if not choice or choice.upper() == "ALL":
        return None
    tokens = choice.replace(",", " ").split()
    selected = set()
    for tok in tokens:
        tok = tok.strip().upper()
        if not tok:
            continue
        if "-" in tok:
            parts = tok.split("-")
            if len(parts) == 2:
                p1 = parts[0].lstrip("Q")
                p2 = parts[1].lstrip("Q")
                if p1.isdigit() and p2.isdigit():
                    for n in range(int(p1), int(p2) + 1):
                        selected.add(f"Q{n}")
                    continue
        if tok.isdigit():
            selected.add(f"Q{tok}")
        elif tok.startswith("Q") and tok[1:].isdigit():
            selected.add(tok)
        else:
            selected.add(tok)
    return selected


def handle_run_queries():
    print_header("6. Analytics Queries (Business Intelligence)")
    list_available_queries()

    print("\nExecution Options:")
    print("  - Press [Enter]   → Run ALL 25 queries")
    print("  - Type query IDs  → Run specific queries (e.g. 'Q1 Q4 Q21' or '1 4 21')")
    print("  - Type range      → Run a range of queries (e.g. '1-5' or 'Q1-Q10')")
    print("  - Type 'B' or '0' → Back to main menu")

    choice = input("\nEnter query selection: ").strip()

    if choice.upper() in ("B", "BACK", "0", "EXIT"):
        return

    selected = parse_query_selection(choice)
    run_queries(only=selected)


def handle_generate_reports():
    print_header("7. Generate Reports (Excel + HTML)")
    print("Options:")
    print("  - Press [Enter]  →  generate BOTH Excel and HTML reports")
    print("  - Type 'E'       →  Excel workbook only")
    print("  - Type 'H'       →  HTML report only")
    choice = input("\nEnter report format choice [Enter/E/H]: ").strip().upper()

    if choice == "E":
        fmt = {"excel"}
    elif choice == "H":
        fmt = {"html"}
    else:
        fmt = {"excel", "html"}

    try:
        outputs = generate_reports(selected_formats=fmt)
        print("\n[COMPLETE] Report generation finished!")
        print("\nGenerated files:")
        for ftype, fpath in outputs.items():
            size_kb = fpath.stat().st_size / 1024
            print(f"  [{ftype.upper():<5}] {fpath.name:<55} ({size_kb:.1f} KB)")
        print(f"\n  All reports saved in: {PROJECT_ROOT / 'reports'}")
    except Exception as e:
        print(f"\n[ERROR] Report generation failed: {e}")
        import traceback
        traceback.print_exc()


def handle_delete_data():
    print_header("8. Delete / Truncate All Data")
    print("WARNING: This will remove ALL rows from all tables in 'staging' and 'dw' schemas!")
    print("The table structures and indexes will remain intact.\n")
    confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()

    if confirm in ("yes", "y"):
        try:
            truncated = truncate_all_warehouse_tables()
            if truncated:
                print("\n[SUCCESS] Successfully truncated tables:")
                for tbl in truncated:
                    print(f"  - {tbl}")
            else:
                print("\n[INFO] No tables found to truncate.")
        except Exception as e:
            print(f"\n[ERROR] Failed to truncate tables: {e}")
    else:
        print("[CANCELLED] Truncate operation aborted.")


def handle_reset_schemas():
    print_header("9. Clean Reset: Drop Schemas from Supabase")
    print("DANGER: This will completely DROP 'staging' and 'dw' schemas (CASCADE)!")
    print("All tables, columns, indexes, and stored data will be deleted.\n")
    confirm = input("Type 'RESET' to confirm schema drop: ").strip()

    if confirm == "RESET":
        try:
            drop_warehouse_schemas()
            print("[SUCCESS] Schemas 'staging' and 'dw' have been completely removed from Supabase.")
            print("You can now run Option 2 to recreate fresh tables from scratch.")
        except Exception as e:
            print(f"\n[ERROR] Failed to drop schemas: {e}")
    else:
        print("[CANCELLED] Schema reset aborted.")


# ─────────────────────────────────────────────────────────────────────────────
HANDLERS = {
    "1":  handle_check_db,
    "2":  handle_create_tables,
    "3":  handle_load_staging,
    "4":  handle_load_reference,
    "5":  handle_build_warehouse,
    "6":  handle_run_queries,
    "7":  handle_generate_reports,
    "8":  handle_delete_data,
    "9":  handle_reset_schemas,
}

EXIT_CHOICES = {"0", "exit", "quit", "q"}


def main():
    while True:
        print_menu()
        choice = input("\nEnter your choice (0-9): ").strip()

        if choice.lower() in EXIT_CHOICES:
            print("\nExiting Warehouse Manager. Goodbye!\n")
            sys.exit(0)

        handler = HANDLERS.get(choice)
        if handler:
            handler()
        else:
            print("[INVALID] Please choose an option between 0 and 9 (or '0' to exit).")
            continue

        input("\nPress [Enter] to return to menu...")


if __name__ == "__main__":
    main()
