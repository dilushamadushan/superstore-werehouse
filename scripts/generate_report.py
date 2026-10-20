"""
Report Generator – Superstore Data Warehouse
==============================================
Coordinator module that executes warehouse analytical queries,
computes key performance indicators (KPIs), and delegates report rendering
to dedicated template generators:
  - scripts/report_excel.py  (Executive-grade multi-sheet Excel workbook)
  - scripts/report_html.py   (Interactive responsive HTML report)

Usage:
  python -m scripts.generate_report
  or call generate_reports() from main.py
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.db import get_engine
from scripts.run_queries import load_queries
from scripts.report_excel import generate_excel_report
from scripts.report_html import generate_html_report

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def generate_reports(selected_formats: set[str] | None = None) -> dict[str, Path]:
    """
    Runs all 25 queries, computes headline KPIs, and generates Excel and/or HTML reports.

    Parameters
    ----------
    selected_formats : set of 'excel' and/or 'html'. None = both.

    Returns
    -------
    dict mapping format name ('excel', 'html') -> output Path
    """
    if selected_formats is None:
        selected_formats = {"excel", "html"}

    engine = get_engine()
    queries = load_queries()

    # 1. Fetch all 25 query DataFrames
    print("\n[REPORT] Running all queries for report generation...")
    all_dfs: dict[str, pd.DataFrame] = {}
    for qid, title, sql in queries:
        try:
            all_dfs[qid] = pd.read_sql(text(sql), engine)
            print(f"  -> {qid}: {len(all_dfs[qid])} rows")
        except Exception as e:
            print(f"  [WARN] {qid} failed: {e}")
            all_dfs[qid] = pd.DataFrame()

    total_rows = sum(len(df) for df in all_dfs.values())
    if total_rows == 0:
        print("  [NOTE] Warehouse tables have no rows or have not been created/built yet.")
        print("         To populate the warehouse, run Menu options 2, 3, 4, then 5.")

    # 2. Compute headline KPIs
    print("[REPORT] Computing headline KPIs...")
    with engine.connect() as conn:
        def qs(sql):
            try:
                return conn.execute(text(sql)).scalar() or 0
            except Exception:
                return 0

        kpis = {
            "total_revenue":   qs("SELECT ROUND(SUM(sales_amount),2) FROM dw.fact_sales;"),
            "total_profit":    qs("SELECT ROUND(SUM(profit),2) FROM dw.fact_sales;"),
            "avg_margin":      qs("""
                SELECT ROUND(SUM(profit)/NULLIF(SUM(sales_amount),0)*100, 2)
                FROM dw.fact_sales;"""),
            "total_orders":    qs("SELECT COUNT(DISTINCT order_id) FROM dw.fact_sales;"),
            "total_customers": qs("SELECT COUNT(*) FROM dw.dim_customer WHERE is_current;"),
            "total_products":  qs("SELECT COUNT(*) FROM dw.dim_product;"),
            "avg_ship_lag":    qs("SELECT ROUND(AVG(ship_lag_days),2) FROM dw.fact_sales;"),
            "promo_orders":    qs("""
                SELECT COUNT(*) FROM dw.fact_sales f
                JOIN dw.dim_promo p USING (promo_key)
                WHERE p.promo_id <> 0;"""),
            "holiday_days":    qs("SELECT COUNT(*) FROM dw.dim_date WHERE is_holiday;"),
        }

    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputs: dict[str, Path] = {}

    # 3. Generate Excel workbook
    if "excel" in selected_formats:
        print("[REPORT] Building Excel workbook (via scripts/report_excel.py)...")
        try:
            xls_path = REPORTS_DIR / f"superstore_report_{ts_str}.xlsx"
            generate_excel_report(xls_path, kpis, all_dfs, ts_str, queries_catalog=queries)
            outputs["excel"] = xls_path
            print(f"  [OK] Excel: {xls_path.name}")
        except Exception as e:
            print(f"  [ERROR] Excel generation failed: {e}")

    # 4. Generate HTML report
    if "html" in selected_formats:
        print("[REPORT] Building HTML report (via scripts/report_html.py)...")
        try:
            html_path = REPORTS_DIR / f"superstore_report_{ts_str}.html"
            generate_html_report(html_path, kpis, all_dfs, ts_str, queries_catalog=queries)
            outputs["html"] = html_path
            print(f"  [OK] HTML:  {html_path.name}")
        except Exception as e:
            print(f"  [ERROR] HTML generation failed: {e}")

    return outputs


if __name__ == "__main__":
    paths = generate_reports()
    for fmt, p in paths.items():
        print(f"[{fmt.upper()}] Saved -> {p}")
