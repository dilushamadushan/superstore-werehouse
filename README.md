# Superstore Cloud Data Warehouse (ETL & Analytics)

An end-to-end cloud Data Warehouse solution built on **PostgreSQL (Supabase)**, **Python**, **SQLAlchemy**, and **Pandas**. 

This repository implements a complete Modern Data Stack workflow:
1. **Staging Ingestion (ELT)**: Ingests raw CSV orders and enriches with external APIs (Nager.Date public holidays) and reference dimensions (stores, marketing promotions).
2. **Dimensional Modeling (Star Schema)**: Transforms flat transactional records into Kimball-style dimensional models (`staging` & `dw` schemas).
3. **Business Intelligence & Analytics**: Executes 25 analytical SQL queries addressing real-world executive questions and automatically exports results to CSV.
4. **Interactive CLI Console**: A unified terminal menu (`main.py`) for managing the entire warehouse lifecycle.

---

## Architecture & Data Flow

```
+-------------------------------------------------------------------------------+
|                               DATA SOURCES                                    |
|   +-----------------------+   +-------------------+   +-------------------+   |
|   | Sample-Superstore.csv |   |  Nager.Date API   |   | Synthetic Promos  |   |
|   |     (9,994 Orders)    |   | (Public Holidays) |   |    & Store Data   |   |
|   +-----------+-----------+   +---------+---------+   +---------+---------+   |
+---------------|-------------------------|-----------------------|-------------+
                |                         |                       |
                v                         v                       v
+-------------------------------------------------------------------------------+
|                              STAGING LAYER (staging)                          |
|   staging.stg_orders (9,994 rows)         staging.stg_holidays (64 rows)      |
|   staging.stg_stores (49 rows)            staging.stg_promotions (21 rows)    |
+---------------------------------------+---------------------------------------+
                                        |
                 [SQL Transformation & Dimensional Mapping]
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                           STAR SCHEMA WAREHOUSE (dw)                          |
|                                                                               |
|   +-------------------+  +-------------------+  +-------------------+         |
|   |    dw.dim_date    |  |  dw.dim_product   |  |  dw.dim_customer  |         |
|   |    (1,461 rows)   |  |   (1,862 rows)    |  |    (793 rows)     |         |
|   +---------+---------+  +---------+---------+  +---------+---------+         |
|             |                      |                      |                   |
|             +-----------------+    |    +-----------------+                   |
|                               |    |    |                                     |
|                               v    v    v                                     |
|                      +------------------------+                               |
|                      |      dw.fact_sales     |                               |
|                      |      (9,994 rows)      |                               |
|                      +------------------------+                               |
|                               ^    ^                                          |
|             +-----------------+    +-----------------+                        |
|             |                                        |                        |
|   +---------+---------+                    +---------+---------+              |
|   |   dw.dim_store    |                    |    dw.dim_promo   |              |
|   |     (49 rows)     |                    |     (21 rows)     |              |
|   +-------------------+                    +-------------------+              |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                            ANALYTICS & REPORTING                              |
|   * 25 Executive BI Queries (sql/02_queries.sql)                              |
|   * Automatic CSV exports saved to results/Q1.csv ... results/Q25.csv         |
+-------------------------------------------------------------------------------+
```

---

## Dimensional Model Design

### Fact Table
- **`dw.fact_sales`**: Grain is one order line item (9,994 rows).
  - **Foreign Keys**: `date_key`, `product_key`, `customer_key`, `store_key`, `promo_key`.
  - **Degenerate Dimension**: `order_id`.
  - **Metrics**: `quantity`, `discount`, `sales_amount`, `profit`.

### Dimension Tables
- **`dw.dim_date`**: Calendar spine from `2014-01-01` to `2017-12-31` (1,461 days) enriched with day/month/quarter/year attributes, weekend indicators, and official US public holidays.
- **`dw.dim_product`**: 1,862 distinct products categorized by `category` and `sub_category`.
- **`dw.dim_customer`**: 793 distinct enterprise and retail customers with `segment` (Consumer, Corporate, Home Office).
- **`dw.dim_store`**: 49 primary regional retail centers (one per US state placed in its highest-order volume city).
- **`dw.dim_promo`**: 21 marketing discount campaigns (New Year, Summer Sale, Back to School, Black Friday, Christmas) plus record `0` for non-promoted orders.

---

## Documentation

- [docs/README.md](docs/README.md) — documentation index
- [docs/project-overview.md](docs/project-overview.md) — warehouse architecture and business purpose
- [docs/setup-guide.md](docs/setup-guide.md) — setup, installation, and environment configuration
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution guidelines and workflow

---

## Project Structure

```text
werehouse/
│
├── data/
│   ├── Sample - Superstore.csv      # Raw source transactions (9,994 rows)
│   └── raw/                         # Raw extracted CSV archives
│       ├── holidays.csv             # API extracts: 64 US holidays (2014-2017)
│       ├── stores.csv               # 49 stores derived from orders
│       └── promotions.csv           # 21 promotional campaigns
│
├── sql/
│   ├── 01_create_warehouse.sql      # Idempotent DDL for schemas, tables & indexes
│   └── 02_queries.sql               # 20 Business Intelligence & Analytics queries
│
├── scripts/
│   ├── db.py                        # Shared connection helper, engine & utilities
│   ├── create_tables.py             # Pre-check, schema creation & status reporter
│   ├── load_staging.py              # Staging loader for superstore orders
│   ├── load_reference_data.py       # API & reference data ingestor
│   ├── build_warehouse.py           # Dimensional Star Schema ETL pipeline
│   └── run_queries.py               # Analytical query runner & CSV exporter
│
├── results/                         # Output folder for analytical query CSVs
│   ├── Q1.csv ... Q20.csv
│
├── main.py                          # Unified Interactive Terminal Console (CLI)
├── requirements.txt                 # Project Python dependencies
└── .env                             # Database connection credentials (git-ignored)
```

---

## Getting Started & Setup

### 1. Prerequisites
- **Python 3.10+**
- **Git**
- A **PostgreSQL** database (e.g. [Supabase](https://supabase.com/))

### 2. Clone and Setup Environment

In your PowerShell or bash terminal:

```powershell
# Navigate into project directory
cd werehouse

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows Command Prompt:
.\venv\Scripts\activate.bat
# Bash:
source venv/Scripts/activate


# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Database Credentials

Create a `.env` file in the project root:

```ini
DB_HOST=aws-0-ap-south-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.your_project_ref
DB_PASSWORD=YourDatabasePassword
DB_URL=postgresql+psycopg2://postgres.your_project_ref:YourDatabasePassword@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
```

> **Important Supabase Notes:**
> - When using the pooler (`*.pooler.supabase.com`), set `DB_PORT=5432` (Session Pooler mode).
> - Make sure the SQLAlchemy URL specifies `postgresql+psycopg2://` and includes `?sslmode=require`.

---

## Running the Project

### Method 1: Interactive Terminal Console (Recommended)

Run the console application from the project root:

```powershell
python main.py
```

You will be presented with a menu:

```text
+--------------------------------------------------------------------------+
|                   SUPERSTORE DATA WAREHOUSE MANAGER                      |
+--------------------------------------------------------------------------+
|  1. Check Database Connection & Table Status                             |
|  2. Create Warehouse Schemas & Tables (staging & dw)                     |
|  3. Load Staging Orders (Superstore CSV -> staging.stg_orders)           |
|  4. Load Reference Data (Holidays API, Stores, Promotions)               |
|  5. Build Data Warehouse (Advanced Star Schema)                          |
|  6. Run Analytics Queries (25 Business Intelligence Questions)           |
|  7. Generate Reports (Excel workbook + HTML report)                      |
|  8. Truncate / Delete All Table Data (keep table structures)             |
|  9. Clean Reset: Drop Schemas from Supabase (DROP staging, dw)           |
|  0. Exit                                                                 |
+--------------------------------------------------------------------------+
```

#### Recommended Execution Order for First Run:
1. Choose **`1`** to verify database connectivity.
2. Choose **`2`** to create schemas and tables (`staging` and `dw`).
3. Choose **`3`** to load the raw orders CSV into `staging.stg_orders`.
4. Choose **`4`** to fetch holidays from Nager.Date API and generate stores & promotions.
5. Choose **`5`** to build the star schema dimensions and fact sales.
6. Choose **`6`** to run executive queries and view analysis.

---

### Method 2: Step-by-Step Script Execution (Command Line)

You can also run individual steps directly via scripts:

#### Step 1: Create Schemas & Tables
```powershell
python scripts/create_tables.py
```
*Validates database objects and idempotently applies `sql/01_create_warehouse.sql`.*

#### Step 2: Ingest Staging Orders
```powershell
python scripts/load_staging.py
```
*Loads 9,994 records from `Sample - Superstore.csv` into `staging.stg_orders`.*

#### Step 3: Ingest Reference Data
```powershell
python scripts/load_reference_data.py
```
*Fetches holidays from Nager.Date API, derives stores, generates promotions, and populates staging.*

#### Step 4: Build Star Schema Dimensional Warehouse
```powershell
python scripts/build_warehouse.py
```
*Transforms and populates all 5 dimension tables and `dw.fact_sales` with automated validation checks.*

#### Step 5: Run Analytics Queries
```powershell
# Run all 20 business queries and export CSVs
python scripts/run_queries.py

# Run specific queries (e.g. Q1, Q6, and Q15)
python scripts/run_queries.py Q1 Q6 Q15

# View list of all 20 questions
python scripts/run_queries.py --list
```

---

## Analytical Queries Overview

The 25 executive queries in [sql/02_queries.sql](sql/02_queries.sql) cover key business domains:

| ID | Business Question / Focus | Key Technique / Dimensions |
| :---: | :--- | :--- |
| **Q1** | Total sales and profit per year | Date aggregation (`year_no`) |
| **Q2** | Monthly sales trend | Time series granularity |
| **Q3** | Quarterly sales breakdown by year | Pivoting using `FILTER (WHERE quarter_no=X)` |
| **Q4** | Top 10 products by sales | Ranked product revenue |
| **Q5** | Bottom 10 products by profit | Loss analysis on product catalog |
| **Q6** | Sales & profit margin % by category | Profit margin ratio calculation |
| **Q7** | Sales by customer segment | Enterprise vs Consumer vs Home Office |
| **Q8** | Top 10 customers by sales & order count | High-value customer identification |
| **Q9** | Sales & profit by geographic region | Regional distribution (East, West, Central, South) |
| **Q10**| Top 5 most profitable states | Geographic margin analysis |
| **Q11**| Best-performing store per quarter | Window ranking (`RANK() OVER (PARTITION BY ...)`) |
| **Q12**| Weekday vs Weekend sales performance | Day type comparison (`is_weekend`) |
| **Q13**| Holiday vs Normal day revenue | Holiday impact analysis (`is_holiday`) |
| **Q14**| Sales with vs without promotions | Promotional lift evaluation |
| **Q15**| Best promotional campaigns by sales | Campaign ROI comparison |
| **Q16**| Discount level vs Profit bands | Elasticity / discount threshold profitability |
| **Q17**| Category sales by region | Multi-dimensional slice and dice |
| **Q18**| Top 15 loss-making products | Negative margin filtering (`HAVING SUM(profit) < 0`) |
| **Q19**| Year-over-year (YoY) sales growth % | Window analytical function (`LAG() OVER ...`) |
| **Q20**| Hierarchical Category & Sub-category subtotals | Dimensional rollups (`GROUP BY ROLLUP(...)`) |

Query outputs are printed to the terminal and automatically saved to:
`results/Q1.csv` through `results/Q25.csv`.

---

## Data Management & Utilities

- **Live Warehouse Health Check**:
  ```powershell
  python scripts/create_tables.py
  ```
  Prints a real-time status matrix showing existence, column counts, and live row counts for all 10 tables.

- **Truncate Warehouse Data**:
  Through Option `7` in `main.py`, or:
  ```python
  from scripts.db import truncate_all_warehouse_tables
  truncate_all_warehouse_tables()
  ```
  Empties all tables with `CASCADE` while preserving table structures and constraints.

- **Full Reset (Drop Schemas)**:
  Through Option `8` in `main.py`, or:
  ```python
  from scripts.db import drop_warehouse_schemas
  drop_warehouse_schemas()
  ```
  Completely drops `staging` and `dw` schemas from Supabase for a clean start.

---

## Troubleshooting

1. **`ModuleNotFoundError: No module named 'dotenv'` or `'psycopg2'`**:
   - Ensure your virtual environment is activated before running:
     `.\venv\Scripts\Activate.ps1`
   - Alternatively, invoke using the venv executable:
     `.\venv\Scripts\python.exe main.py`

2. **Supabase Connection Timeout (`timeout expired` / `server closed connection`)**:
   - Verify that your IP has internet access to Supabase.
   - Ensure `.env` uses `DB_PORT=5432` for Session Pooler mode.
   - Confirm your `DB_USER` uses the format `postgres.<project-ref>`.

3. **Windows PowerShell Execution Policy Error (`Activate.ps1 cannot be loaded`)**:
   - Run in PowerShell:
     `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## License

This project is open-source and intended for educational and data engineering portfolio demonstration.
