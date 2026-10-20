"""
Warehouse Builder (Advanced):
Transforms data from 'staging' schema into the Star Schema 'dw' (Dimensional Model).

Dimensions built:
  - dim_date       : Full calendar 2014–2017 with holiday, weekend, fiscal-quarter flags
  - dim_product    : Product hierarchy (category / sub_category / product)
  - dim_customer   : SCD Type 2 – tracks segment changes over time
  - dim_store      : State-level store dimension
  - dim_promo      : Promotional campaigns (id=0 sentinel for no-promo)
  - dim_ship_mode  : Shipping method with speed tier classification

Fact table enrichments:
  - ship_date_key  : FK to dim_date for ship date
  - ship_lag_days  : Days between order and shipment
  - profit_margin  : profit / sales_amount
  - discount_band  : Bucketed discount label
"""

import sys
from pathlib import Path
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.db import get_engine


# ---------------------------------------------------------------------------
# Ordered ETL steps
# ---------------------------------------------------------------------------
STEPS = [
    (
        "Patch schema columns",
        """
        -- Widen fiscal_quarter if it was created as VARCHAR(6) — needs VARCHAR(10) for "FY2014Q1"
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'dim_date'
                  AND column_name = 'fiscal_quarter'
                  AND character_maximum_length < 10
            ) THEN
                ALTER TABLE dw.dim_date ALTER COLUMN fiscal_quarter TYPE VARCHAR(10);
            END IF;
            -- Add dim_ship_mode table if it doesn't exist yet (schema migration safety)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'dw' AND table_name = 'dim_ship_mode'
            ) THEN
                CREATE TABLE dw.dim_ship_mode (
                    ship_mode_key  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    ship_mode_name VARCHAR(30) NOT NULL UNIQUE,
                    speed_tier     VARCHAR(20)
                );
            END IF;
            -- Add ship_date_key column to fact_sales if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'fact_sales'
                  AND column_name = 'ship_date_key'
            ) THEN
                ALTER TABLE dw.fact_sales ADD COLUMN ship_date_key INT;
            END IF;
            -- Add ship_mode_key column to fact_sales if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'fact_sales'
                  AND column_name = 'ship_mode_key'
            ) THEN
                ALTER TABLE dw.fact_sales ADD COLUMN ship_mode_key INT;
            END IF;
            -- Add ship_lag_days column to fact_sales if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'fact_sales'
                  AND column_name = 'ship_lag_days'
            ) THEN
                ALTER TABLE dw.fact_sales ADD COLUMN ship_lag_days SMALLINT;
            END IF;
            -- Add profit_margin column to fact_sales if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'fact_sales'
                  AND column_name = 'profit_margin'
            ) THEN
                ALTER TABLE dw.fact_sales ADD COLUMN profit_margin NUMERIC(6,4);
            END IF;
            -- Add discount_band column to fact_sales if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'fact_sales'
                  AND column_name = 'discount_band'
            ) THEN
                ALTER TABLE dw.fact_sales ADD COLUMN discount_band VARCHAR(20);
            END IF;
            -- Add week_of_year to dim_date if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'dim_date'
                  AND column_name = 'week_of_year'
            ) THEN
                ALTER TABLE dw.dim_date ADD COLUMN week_of_year SMALLINT;
            END IF;
            -- Add fiscal_quarter to dim_date if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'dim_date'
                  AND column_name = 'fiscal_quarter'
            ) THEN
                ALTER TABLE dw.dim_date ADD COLUMN fiscal_quarter VARCHAR(10);
            END IF;
            -- Add SCD columns to dim_customer if missing
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'dw' AND table_name = 'dim_customer'
                  AND column_name = 'effective_date'
            ) THEN
                ALTER TABLE dw.dim_customer
                    ADD COLUMN effective_date DATE NOT NULL DEFAULT '2014-01-01',
                    ADD COLUMN expiry_date    DATE,
                    ADD COLUMN is_current     BOOLEAN DEFAULT TRUE;
            END IF;
        END $$;
        """,
    ),
    (
        "Clear warehouse tables",
        """
        TRUNCATE dw.fact_sales, dw.dim_date, dw.dim_product, dw.dim_customer,
                 dw.dim_store, dw.dim_promo, dw.dim_ship_mode
        RESTART IDENTITY CASCADE;
        """,
    ),
    # ------------------------------------------------------------------ dim_date
    (
        "dim_date",
        """
        INSERT INTO dw.dim_date (
            date_key, full_date, day_name, day_of_month, month_no, month_name,
            quarter_no, year_no, week_of_year, is_weekend, is_holiday, holiday_name,
            fiscal_quarter
        )
        SELECT
            to_char(g.d, 'YYYYMMDD')::int,
            g.d::date,
            trim(to_char(g.d, 'Day')),
            EXTRACT(day   FROM g.d)::smallint,
            EXTRACT(month FROM g.d)::smallint,
            trim(to_char(g.d, 'Month')),
            EXTRACT(quarter FROM g.d)::smallint,
            EXTRACT(year    FROM g.d)::smallint,
            EXTRACT(week    FROM g.d)::smallint,
            EXTRACT(isodow  FROM g.d) IN (6, 7),
            h.holiday_name IS NOT NULL,
            h.holiday_name,
            'FY' || EXTRACT(year FROM g.d)::text || 'Q' ||
                    EXTRACT(quarter FROM g.d)::text
        FROM generate_series(
            (SELECT MIN(order_date) FROM staging.stg_orders),
            (SELECT MAX(ship_date)  FROM staging.stg_orders),
            '1 day'
        ) AS g(d)
        LEFT JOIN (
            SELECT holiday_date, MIN(holiday_name) AS holiday_name
            FROM staging.stg_holidays
            GROUP BY holiday_date
        ) h ON h.holiday_date = g.d::date;
        """,
    ),

    # --------------------------------------------------------------- dim_ship_mode
    (
        "dim_ship_mode",
        """
        INSERT INTO dw.dim_ship_mode (ship_mode_name, speed_tier)
        SELECT DISTINCT ship_mode,
            CASE ship_mode
                WHEN 'Same Day'        THEN 'Same Day'
                WHEN 'First Class'     THEN 'Express'
                WHEN 'Second Class'    THEN 'Standard'
                WHEN 'Standard Class'  THEN 'Economy'
                ELSE 'Other'
            END
        FROM staging.stg_orders
        ORDER BY ship_mode;
        """,
    ),
    # --------------------------------------------------------------- dim_product
    (
        "dim_product",
        """
        INSERT INTO dw.dim_product (product_id, product_name, sub_category, category)
        SELECT DISTINCT ON (product_id) product_id, product_name, sub_category, category
        FROM staging.stg_orders
        ORDER BY product_id, product_name;
        """,
    ),
    # -------------------------------------------------------------- dim_customer (SCD Type 2)
    (
        "dim_customer (SCD2)",
        """
        INSERT INTO dw.dim_customer (
            customer_id, customer_name, segment,
            effective_date, expiry_date, is_current
        )
        -- One current record per customer (effective 2014-01-01, no expiry)
        SELECT DISTINCT ON (customer_id)
            customer_id, customer_name, segment,
            MIN(order_date) OVER (PARTITION BY customer_id) AS effective_date,
            NULL::date,
            TRUE
        FROM staging.stg_orders
        ORDER BY customer_id, order_date;
        """,
    ),
    # ---------------------------------------------------------------- dim_store
    (
        "dim_store",
        """
        INSERT INTO dw.dim_store (store_id, store_name, city, state, region)
        SELECT store_id, store_name, city, state, region
        FROM staging.stg_stores
        ORDER BY store_id;
        """,
    ),
    # ----------------------------------------------------------------- dim_promo
    (
        "dim_promo",
        """
        INSERT INTO dw.dim_promo (promo_id, promo_name, promo_type, discount_pct, start_date, end_date)
        SELECT promo_id, promo_name, promo_type, discount_pct, start_date, end_date
        FROM staging.stg_promotions
        ORDER BY promo_id;
        """,
    ),
    # --------------------------------------------------------------- fact_sales
    (
        "fact_sales",
        """
        INSERT INTO dw.fact_sales (
            date_key, ship_date_key, product_key, customer_key, store_key, promo_key,
            ship_mode_key, order_id, quantity, discount, sales_amount, profit,
            ship_lag_days, profit_margin, discount_band
        )
        SELECT
            to_char(o.order_date, 'YYYYMMDD')::int          AS date_key,
            to_char(o.ship_date,  'YYYYMMDD')::int          AS ship_date_key,
            p.product_key,
            c.customer_key,
            s.store_key,
            COALESCE(pr.promo_key, np.promo_key)            AS promo_key,
            sm.ship_mode_key,
            o.order_id,
            o.quantity,
            o.discount,
            ROUND(o.sales,   2)                             AS sales_amount,
            ROUND(o.profit,  2)                             AS profit,
            (o.ship_date - o.order_date)::smallint          AS ship_lag_days,
            CASE WHEN o.sales = 0 THEN 0
                 ELSE ROUND(o.profit / o.sales, 4)
            END                                             AS profit_margin,
            CASE
                WHEN o.discount = 0          THEN '0-None'
                WHEN o.discount <= 0.20      THEN '1-Low (0-20%)'
                WHEN o.discount <= 0.40      THEN '2-Mid (21-40%)'
                ELSE                              '3-High (>40%)'
            END                                             AS discount_band
        FROM staging.stg_orders o
        JOIN dw.dim_product  p  ON p.product_id   = o.product_id
        JOIN dw.dim_customer c  ON c.customer_id  = o.customer_id AND c.is_current = TRUE
        JOIN dw.dim_store    s  ON s.state         = o.state
        JOIN dw.dim_ship_mode sm ON sm.ship_mode_name = o.ship_mode
        LEFT JOIN dw.dim_promo pr
            ON pr.promo_id <> 0
           AND o.order_date BETWEEN pr.start_date AND pr.end_date
        CROSS JOIN (SELECT promo_key FROM dw.dim_promo WHERE promo_id = 0) np;
        """,
    ),
]


# ---------------------------------------------------------------------------
# Staging readiness check
# ---------------------------------------------------------------------------
def check_staging_readiness(engine) -> list[str]:
    """Verifies that all required staging tables have records."""
    required = ["stg_orders", "stg_holidays", "stg_stores", "stg_promotions"]
    empty = []
    with engine.connect() as conn:
        for tbl in required:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM staging.{tbl};")).scalar() or 0
            if cnt == 0:
                empty.append(tbl)
    return empty


# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------
def build_warehouse() -> dict:
    """Executes warehouse dimensional build and returns validation metrics."""
    engine = get_engine()

    missing_staging = check_staging_readiness(engine)
    if missing_staging:
        raise RuntimeError(
            f"Cannot build warehouse – staging table(s) with 0 rows:\n"
            f"  {', '.join([f'staging.{t}' for t in missing_staging])}\n"
            f"Run Options 3 & 4 first."
        )

    print("\nExecuting Warehouse Build (Advanced Star Schema):")
    col_w = 30
    with engine.begin() as conn:
        for name, sql in STEPS:
            res = conn.execute(text(sql))
            rows_affected = (
                res.rowcount if res.rowcount is not None and res.rowcount >= 0 else "done"
            )
            print(f"  -> {name:<{col_w}} rows affected: {rows_affected}")

    # ---------------------------------------------------------------- Validation
    metrics: dict = {}
    print("\nWarehouse Validation:")
    with engine.connect() as conn:
        q = lambda s: conn.execute(text(s)).scalar()

        stg  = q("SELECT COUNT(*) FROM staging.stg_orders;")
        fact = q("SELECT COUNT(*) FROM dw.fact_sales;")
        match = stg == fact
        metrics["stg_orders"] = stg
        metrics["fact_sales"] = fact
        metrics["match"]      = match

        print(f"  * staging.stg_orders rows: {stg:,}")
        print(f"  * dw.fact_sales rows:      {fact:,}")
        print(f"  * 1-to-1 match check:      {'PASSED [OK]' if match else 'FAILED [MISMATCH]'}")

        for t in ("dim_date", "dim_product", "dim_customer", "dim_store", "dim_promo", "dim_ship_mode"):
            cnt = q(f"SELECT COUNT(*) FROM dw.{t};")
            metrics[t] = cnt
            print(f"  * dw.{t:<18} {cnt:,} rows")

        promo_orders  = q("""
            SELECT COUNT(*) FROM dw.fact_sales f
            JOIN dw.dim_promo p USING (promo_key)
            WHERE p.promo_id <> 0;
        """)
        holiday_days  = q("SELECT COUNT(*) FROM dw.dim_date WHERE is_holiday;")
        avg_ship_lag  = q("SELECT ROUND(AVG(ship_lag_days), 2) FROM dw.fact_sales;")
        metrics["promo_orders"]  = promo_orders
        metrics["holiday_days"]  = holiday_days
        metrics["avg_ship_lag"]  = avg_ship_lag

        print(f"  * Orders assigned to promotions:   {promo_orders:,}")
        print(f"  * Holiday dates in dim_date:       {holiday_days:,}")
        print(f"  * Avg shipment lag (days):         {avg_ship_lag}")

    return metrics


if __name__ == "__main__":
    build_warehouse()