"""
Load Reference Data into Staging:
- Public holidays via Nager.Date API -> staging.stg_holidays & data/raw/holidays.csv
- Store dimension base data derived from orders -> staging.stg_stores & data/raw/stores.csv
- Promotional campaigns catalog -> staging.stg_promotions & data/raw/promotions.csv
"""

import sys
from pathlib import Path
import pandas as pd
import requests
from sqlalchemy import text

# Ensure scripts directory and root are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.db import get_engine

RAW = PROJECT_ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def load_holidays(engine=None, country="US", years=range(2014, 2018)) -> int:
    """Fetches public holidays from Nager.Date API and populates staging.stg_holidays."""
    if engine is None:
        engine = get_engine()

    print("[HOLIDAYS] Fetching public holidays from Nager.Date API...")
    rows = []
    for y in years:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{y}/{country}"
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            holidays = r.json()
            rows += [
                {
                    "holiday_date": h["date"],
                    "holiday_name": h["name"],
                    "country_code": country,
                }
                for h in holidays
            ]
        except Exception as e:
            print(f"  [WARN] Failed fetching year {y} from API: {e}")

    if not rows:
        raise RuntimeError("No holidays could be retrieved from the API.")

    df = pd.DataFrame(rows)
    df["holiday_date"] = pd.to_datetime(df["holiday_date"])
    df.to_csv(RAW / "holidays.csv", index=False)
    print(f"  -> Saved {len(df)} records to data/raw/holidays.csv")

    with engine.begin() as c:
        c.execute(text("TRUNCATE staging.stg_holidays;"))
    df.to_sql("stg_holidays", engine, schema="staging", if_exists="append", index=False)
    return len(df)


def load_stores(engine=None) -> int:
    """
    Derives one primary store per state placed in that state's busiest city
    based on staging.stg_orders data, and populates staging.stg_stores.
    """
    if engine is None:
        engine = get_engine()

    print("[STORES] Deriving store locations from staging.stg_orders...")
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM staging.stg_orders;")).scalar() or 0
        if count == 0:
            raise RuntimeError(
                "staging.stg_orders is empty! Please load staging data first (Option 3 in main.py)."
            )

    o = pd.read_sql(
        "SELECT state, region, city, COUNT(*) AS n "
        "FROM staging.stg_orders GROUP BY state, region, city;",
        engine,
    )
    top = (
        o.sort_values("n", ascending=False)
        .drop_duplicates("state")
        .sort_values("state")
        .reset_index(drop=True)
    )
    top["store_id"] = top.index + 1
    top["store_name"] = top.apply(lambda r: f"Store {r.store_id:02d} - {r.city}", axis=1)
    df = top[["store_id", "store_name", "city", "state", "region"]]
    df.to_csv(RAW / "stores.csv", index=False)
    print(f"  -> Saved {len(df)} stores to data/raw/stores.csv")

    with engine.begin() as c:
        c.execute(text("TRUNCATE staging.stg_stores;"))
    df.to_sql("stg_stores", engine, schema="staging", if_exists="append", index=False)
    return len(df)


def load_promotions(engine=None) -> int:
    """Generates promotional campaigns and populates staging.stg_promotions."""
    if engine is None:
        engine = get_engine()

    print("[PROMOTIONS] Generating promotional campaigns catalog...")
    rows = [(0, "No promotion", "None", 0, None, None)]
    pid = 1
    for y in range(2014, 2018):
        for name, ptype, pct, s, e in [
            ("New Year Offer", "Festive", 15, f"{y}-01-01", f"{y}-01-10"),
            ("Summer Sale", "Seasonal", 20, f"{y}-06-15", f"{y}-06-30"),
            ("Back to School", "Seasonal", 10, f"{y}-08-01", f"{y}-08-15"),
            ("Black Friday", "Seasonal", 30, f"{y}-11-20", f"{y}-11-30"),
            ("Christmas Sale", "Festive", 20, f"{y}-12-15", f"{y}-12-31"),
        ]:
            rows.append((pid, f"{name} {y}", ptype, pct, s, e))
            pid += 1

    df = pd.DataFrame(
        rows,
        columns=["promo_id", "promo_name", "promo_type", "discount_pct", "start_date", "end_date"],
    )
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df.to_csv(RAW / "promotions.csv", index=False)
    print(f"  -> Saved {len(df)} promotions to data/raw/promotions.csv")

    with engine.begin() as c:
        c.execute(text("TRUNCATE staging.stg_promotions;"))
    df.to_sql("stg_promotions", engine, schema="staging", if_exists="append", index=False)
    return len(df)


def load_reference_data():
    """Runs all reference data loading steps and returns summary dict."""
    engine = get_engine()
    h = load_holidays(engine)
    s = load_stores(engine)
    p = load_promotions(engine)

    print("\n[COMPLETE] Reference Data Summary:")
    print(f"  - Holidays loaded:   {h}")
    print(f"  - Stores loaded:     {s}")
    print(f"  - Promotions loaded: {p}")
    return {"holidays": h, "stores": s, "promotions": p}


if __name__ == "__main__":
    load_reference_data()