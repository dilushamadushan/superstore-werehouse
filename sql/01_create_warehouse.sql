-- ============================================================
--  Superstore Data Warehouse  |  Schema: staging + dw
--  Advanced Star Schema with SCD Type 2 on dim_customer,
--  dim_ship_mode dimension, and enriched fact_sales
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;

-- ============================================================
--  STAGING TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS staging.stg_orders (
    row_id        INT,
    order_id      VARCHAR(30),
    order_date    DATE,
    ship_date     DATE,
    ship_mode     VARCHAR(30),
    customer_id   VARCHAR(20),
    customer_name VARCHAR(100),
    segment       VARCHAR(30),
    country       VARCHAR(50),
    city          VARCHAR(100),
    state         VARCHAR(100),
    postal_code   VARCHAR(10),
    region        VARCHAR(20),
    product_id    VARCHAR(30),
    category      VARCHAR(50),
    sub_category  VARCHAR(50),
    product_name  VARCHAR(255),
    sales         NUMERIC(12,4),
    quantity      INT,
    discount      NUMERIC(5,2),
    profit        NUMERIC(12,4)
);

CREATE TABLE IF NOT EXISTS staging.stg_holidays (
    holiday_date  DATE,
    holiday_name  VARCHAR(150),
    country_code  VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS staging.stg_stores (
    store_id    INT,
    store_name  VARCHAR(100),
    city        VARCHAR(100),
    state       VARCHAR(100),
    region      VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS staging.stg_promotions (
    promo_id      INT,
    promo_name    VARCHAR(100),
    promo_type    VARCHAR(30),
    discount_pct  NUMERIC(5,2),
    start_date    DATE,
    end_date      DATE
);

-- ============================================================
--  DIMENSION TABLES
-- ============================================================

-- dim_date: calendar & holiday enrichment
CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key       INT PRIMARY KEY,           -- YYYYMMDD
    full_date      DATE NOT NULL UNIQUE,
    day_name       VARCHAR(10),
    day_of_month   SMALLINT,
    month_no       SMALLINT,
    month_name     VARCHAR(10),
    quarter_no     SMALLINT,
    year_no        SMALLINT,
    week_of_year   SMALLINT,
    is_weekend     BOOLEAN,
    is_holiday     BOOLEAN DEFAULT FALSE,
    holiday_name   VARCHAR(150),
    fiscal_quarter VARCHAR(10)                -- e.g. FY2014Q1
);

-- dim_product: product hierarchy
CREATE TABLE IF NOT EXISTS dw.dim_product (
    product_key   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id    VARCHAR(30) NOT NULL UNIQUE,
    product_name  VARCHAR(255),
    sub_category  VARCHAR(50),
    category      VARCHAR(50)
);

-- dim_customer: SCD Type 2 (tracks segment changes over time)
CREATE TABLE IF NOT EXISTS dw.dim_customer (
    customer_key   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id    VARCHAR(20) NOT NULL,
    customer_name  VARCHAR(100),
    segment        VARCHAR(30),
    effective_date DATE NOT NULL DEFAULT '2014-01-01',
    expiry_date    DATE,                      -- NULL = currently active record
    is_current     BOOLEAN DEFAULT TRUE,
    UNIQUE (customer_id, effective_date)
);

-- dim_store: state-level store dimension
CREATE TABLE IF NOT EXISTS dw.dim_store (
    store_key     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id      INT NOT NULL UNIQUE,
    store_name    VARCHAR(100),
    city          VARCHAR(100),
    state         VARCHAR(100),
    region        VARCHAR(20)
);

-- dim_promo: promotional campaigns (id=0 = no promotion sentinel)
CREATE TABLE IF NOT EXISTS dw.dim_promo (
    promo_key     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    promo_id      INT NOT NULL UNIQUE,
    promo_name    VARCHAR(100),
    promo_type    VARCHAR(30),
    discount_pct  NUMERIC(5,2),
    start_date    DATE,
    end_date      DATE
);

-- dim_ship_mode: shipping method dimension
CREATE TABLE IF NOT EXISTS dw.dim_ship_mode (
    ship_mode_key  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ship_mode_name VARCHAR(30) NOT NULL UNIQUE,
    speed_tier     VARCHAR(20)               -- Same Day / Express / Standard / Economy
);

-- ============================================================
--  FACT TABLE  (enriched)
-- ============================================================

CREATE TABLE IF NOT EXISTS dw.fact_sales (
    sales_key      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date_key       INT NOT NULL REFERENCES dw.dim_date(date_key),
    ship_date_key  INT REFERENCES dw.dim_date(date_key),
    product_key    INT NOT NULL REFERENCES dw.dim_product(product_key),
    customer_key   INT NOT NULL REFERENCES dw.dim_customer(customer_key),
    store_key      INT NOT NULL REFERENCES dw.dim_store(store_key),
    promo_key      INT NOT NULL REFERENCES dw.dim_promo(promo_key),
    ship_mode_key  INT REFERENCES dw.dim_ship_mode(ship_mode_key),
    order_id       VARCHAR(30),
    quantity       INT,
    discount       NUMERIC(5,2),
    sales_amount   NUMERIC(12,2),
    profit         NUMERIC(12,2),
    ship_lag_days  SMALLINT,                 -- days between order and ship
    profit_margin  NUMERIC(6,4),             -- profit / sales_amount
    discount_band  VARCHAR(20)               -- derived discount bucket
);

-- ============================================================
--  PERFORMANCE INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fact_date          ON dw.fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_ship_date     ON dw.fact_sales(ship_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_product       ON dw.fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_customer      ON dw.fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_store         ON dw.fact_sales(store_key);
CREATE INDEX IF NOT EXISTS idx_fact_promo         ON dw.fact_sales(promo_key);
CREATE INDEX IF NOT EXISTS idx_fact_ship_mode     ON dw.fact_sales(ship_mode_key);
CREATE INDEX IF NOT EXISTS idx_fact_order_id      ON dw.fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_customer_scd       ON dw.dim_customer(customer_id, is_current);
CREATE INDEX IF NOT EXISTS idx_date_year_quarter  ON dw.dim_date(year_no, quarter_no);