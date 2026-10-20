"""
Analytics Query Runner:
Executes the 20 Superstore business intelligence queries defined in sql/02_queries.sql.
Outputs tabular results to terminal and exports CSVs to the results/ directory.
Uses pure ASCII characters for 100% Windows console compatibility.
"""

import re
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

# Ensure scripts directory and root are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.db import get_engine

SQL_FILE = PROJECT_ROOT / "sql" / "02_queries.sql"
OUT = PROJECT_ROOT / "results"
OUT.mkdir(exist_ok=True)


def load_queries() -> list[tuple[str, str, str]]:
    """
    Parses sql/02_queries.sql into a list of (qid, title, sql) tuples.
    """
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"Queries file not found at: {SQL_FILE}")

    content = SQL_FILE.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^-- (Q\d+): ?(.*)$", content)

    queries = []
    for i in range(1, len(parts), 3):
        qid = parts[i].strip()
        title = parts[i + 1].strip()
        sql = parts[i + 2].strip()
        queries.append((qid, title, sql))
    return queries


CATEGORIES = [
    ("TIME & TRENDS", ["Q1", "Q2", "Q3", "Q12", "Q13", "Q19", "Q24"]),
    ("PRODUCTS & PROFITABILITY", ["Q4", "Q5", "Q6", "Q18", "Q20", "Q22"]),
    ("CUSTOMERS & ORDERS", ["Q7", "Q8", "Q23", "Q25"]),
    ("GEOGRAPHY & STORES", ["Q9", "Q10", "Q11", "Q17"]),
    ("PROMOTIONS, PRICING & OPERATIONS", ["Q14", "Q15", "Q16", "Q21"]),
]


def list_available_queries():
    """Prints a clean list of all 25 queries showing only ID and query name."""
    queries_dict = {qid: title for qid, title, _ in load_queries()}

    print("\nAvailable Analytical Queries (25 Total):")
    for cat_name, qids in CATEGORIES:
        print(f"\n  [{cat_name}]")
        for qid in qids:
            title = queries_dict.get(qid, "")
            print(f"    {qid:<5}: {title}")


def run_queries(only: set[str] | list[str] | None = None, save_csv: bool = True) -> int:
    """
    Executes specified queries (or all if only=None), prints formatted tables,
    and exports CSV files to results/ directory.
    Returns the count of queries executed.
    """
    engine = get_engine()
    queries = load_queries()

    if only:
        target_ids = {str(x).strip().upper() for x in only}
    else:
        target_ids = None

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 100)

    executed_count = 0
    print("\n" + "=" * 80)
    print("Running Superstore Warehouse Analytical Queries -> Output: results/")
    print("=" * 80)

    for qid, title, sql in queries:
        if target_ids and qid.upper() not in target_ids:
            continue

        executed_count += 1
        print("\n" + "-" * 80)
        print(f"[{qid}] {title}")
        print("-" * 80)

        try:
            df = pd.read_sql(text(sql), engine)
            if save_csv:
                csv_path = OUT / f"{qid}.csv"
                df.to_csv(csv_path, index=False)

            print(df.to_string(index=False))
            print(f"\n({len(df)} row{'s' if len(df) != 1 else ''} returned | Saved: results/{qid}.csv)")

        except Exception as e:
            print(f"[ERROR executing {qid}]: {e}")

    print("\n" + "=" * 80)
    print(f"Completed {executed_count} quer{'ies' if executed_count != 1 else 'y'}.")
    print("=" * 80)
    return executed_count


if __name__ == "__main__":
    args = [a.strip() for a in sys.argv[1:]]
    if "--list" in args or "-l" in args:
        list_available_queries()
    else:
        filter_qids = {a.upper() for a in args if not a.startswith("-")}
        run_queries(only=filter_qids if filter_qids else None)