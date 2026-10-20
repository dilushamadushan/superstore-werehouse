-- ============================================================
--  Superstore Data Warehouse – 25 Business Intelligence Queries
--  Uses the advanced star schema (dim_ship_mode, enriched fact)
-- ============================================================

-- Q1: Total sales and profit per year
SELECT d.year_no,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct
FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
GROUP BY d.year_no ORDER BY d.year_no;

-- Q2: Monthly sales trend
SELECT d.year_no, d.month_no, d.month_name,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit
FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
GROUP BY d.year_no, d.month_no, d.month_name ORDER BY d.year_no, d.month_no;

-- Q3: Quarterly sales by year (pivot)
SELECT d.year_no,
  ROUND(SUM(f.sales_amount) FILTER (WHERE d.quarter_no = 1), 2) AS q1,
  ROUND(SUM(f.sales_amount) FILTER (WHERE d.quarter_no = 2), 2) AS q2,
  ROUND(SUM(f.sales_amount) FILTER (WHERE d.quarter_no = 3), 2) AS q3,
  ROUND(SUM(f.sales_amount) FILTER (WHERE d.quarter_no = 4), 2) AS q4
FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
GROUP BY d.year_no ORDER BY d.year_no;

-- Q4: Top 10 products by sales
SELECT p.product_name, p.category,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit
FROM dw.fact_sales f JOIN dw.dim_product p USING (product_key)
GROUP BY p.product_name, p.category ORDER BY total_sales DESC LIMIT 10;

-- Q5: Bottom 10 products by profit (loss-leaders)
SELECT p.product_name, p.category,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM dw.fact_sales f JOIN dw.dim_product p USING (product_key)
GROUP BY p.product_name, p.category ORDER BY total_profit ASC LIMIT 10;

-- Q6: Sales and profit margin by category
SELECT p.category,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct
FROM dw.fact_sales f JOIN dw.dim_product p USING (product_key)
GROUP BY p.category ORDER BY total_sales DESC;

-- Q7: Sales by customer segment
SELECT c.segment,
       COUNT(DISTINCT c.customer_key)  AS customers,
       ROUND(SUM(f.sales_amount), 2)   AS total_sales,
       ROUND(SUM(f.profit),       2)   AS total_profit,
       ROUND(AVG(f.sales_amount), 2)   AS avg_order_value
FROM dw.fact_sales f JOIN dw.dim_customer c USING (customer_key)
GROUP BY c.segment ORDER BY total_sales DESC;

-- Q8: Top 10 customers by sales
SELECT c.customer_name, c.segment,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       COUNT(DISTINCT f.order_id)    AS total_orders,
       ROUND(SUM(f.profit),       2) AS total_profit
FROM dw.fact_sales f JOIN dw.dim_customer c USING (customer_key)
GROUP BY c.customer_name, c.segment ORDER BY total_sales DESC LIMIT 10;

-- Q9: Sales by region
SELECT s.region,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct
FROM dw.fact_sales f JOIN dw.dim_store s USING (store_key)
GROUP BY s.region ORDER BY total_sales DESC;

-- Q10: Top 5 states by profit
SELECT s.state, s.region,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM dw.fact_sales f JOIN dw.dim_store s USING (store_key)
GROUP BY s.state, s.region ORDER BY total_profit DESC LIMIT 5;

-- Q11: Best-performing store per quarter (ranking window function)
WITH ranked AS (
  SELECT d.year_no, d.quarter_no, st.store_name,
         SUM(f.sales_amount) AS total,
         RANK() OVER (PARTITION BY d.year_no, d.quarter_no ORDER BY SUM(f.sales_amount) DESC) AS rk
  FROM dw.fact_sales f
  JOIN dw.dim_date  d  USING (date_key)
  JOIN dw.dim_store st USING (store_key)
  GROUP BY d.year_no, d.quarter_no, st.store_name
)
SELECT year_no, quarter_no, store_name, ROUND(total, 2) AS total_sales
FROM ranked WHERE rk = 1 ORDER BY year_no, quarter_no;

-- Q12: Weekday vs weekend sales
SELECT CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       COUNT(*)                                                   AS order_lines,
       ROUND(SUM(f.sales_amount), 2)                             AS total_sales,
       ROUND(SUM(f.sales_amount) / COUNT(DISTINCT d.date_key), 2) AS avg_sales_per_day
FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
GROUP BY d.is_weekend;

-- Q13: Holiday vs normal day sales
SELECT CASE WHEN d.is_holiday THEN 'Holiday' ELSE 'Normal day' END AS day_type,
       COUNT(DISTINCT d.date_key)                                    AS days_with_sales,
       ROUND(SUM(f.sales_amount), 2)                                 AS total_sales,
       ROUND(SUM(f.sales_amount) / COUNT(DISTINCT d.date_key), 2)   AS avg_sales_per_day
FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
GROUP BY d.is_holiday;

-- Q14: Sales with vs without promotion
SELECT CASE WHEN p.promo_id = 0 THEN 'No Promotion' ELSE 'Promotion' END AS promo_status,
       COUNT(*)                          AS order_lines,
       ROUND(SUM(f.sales_amount), 2)    AS total_sales,
       ROUND(AVG(f.sales_amount), 2)    AS avg_line_sales,
       ROUND(SUM(f.profit),       2)    AS total_profit
FROM dw.fact_sales f JOIN dw.dim_promo p USING (promo_key)
GROUP BY promo_status;

-- Q15: Best promotions by sales
SELECT p.promo_name, p.promo_type, p.discount_pct,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit
FROM dw.fact_sales f JOIN dw.dim_promo p USING (promo_key)
WHERE p.promo_id <> 0
GROUP BY p.promo_name, p.promo_type, p.discount_pct ORDER BY total_sales DESC LIMIT 10;

-- Q16: Discount band vs profit analysis
SELECT f.discount_band,
       COUNT(*)                       AS order_lines,
       ROUND(SUM(f.sales_amount), 2)  AS total_sales,
       ROUND(SUM(f.profit),       2)  AS total_profit,
       ROUND(AVG(f.profit_margin) * 100, 2) AS avg_margin_pct
FROM dw.fact_sales f
GROUP BY f.discount_band ORDER BY f.discount_band;

-- Q17: Category sales by region (slice and dice)
SELECT p.category,
  ROUND(SUM(f.sales_amount) FILTER (WHERE s.region = 'East'),    2) AS east,
  ROUND(SUM(f.sales_amount) FILTER (WHERE s.region = 'West'),    2) AS west,
  ROUND(SUM(f.sales_amount) FILTER (WHERE s.region = 'Central'), 2) AS central,
  ROUND(SUM(f.sales_amount) FILTER (WHERE s.region = 'South'),   2) AS south
FROM dw.fact_sales f
JOIN dw.dim_product p USING (product_key)
JOIN dw.dim_store   s USING (store_key)
GROUP BY p.category ORDER BY p.category;

-- Q18: Loss-making products
SELECT p.product_name, p.sub_category,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       SUM(f.quantity)               AS units_sold
FROM dw.fact_sales f JOIN dw.dim_product p USING (product_key)
GROUP BY p.product_name, p.sub_category HAVING SUM(f.profit) < 0
ORDER BY total_profit ASC LIMIT 15;

-- Q19: Year-over-year sales growth
WITH yearly AS (
  SELECT d.year_no, SUM(f.sales_amount) AS sales
  FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
  GROUP BY d.year_no
)
SELECT year_no,
       ROUND(sales, 2) AS total_sales,
       ROUND(LAG(sales) OVER (ORDER BY year_no), 2) AS prev_year_sales,
       ROUND((sales - LAG(sales) OVER (ORDER BY year_no))
             / NULLIF(LAG(sales) OVER (ORDER BY year_no), 0) * 100, 2) AS growth_pct
FROM yearly ORDER BY year_no;

-- Q20: Category and sub-category subtotals (ROLLUP)
SELECT COALESCE(p.category,     'ALL CATEGORIES') AS category,
       COALESCE(p.sub_category, 'Subtotal')        AS sub_category,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit
FROM dw.fact_sales f JOIN dw.dim_product p USING (product_key)
GROUP BY ROLLUP (p.category, p.sub_category)
ORDER BY p.category NULLS LAST, p.sub_category NULLS LAST;

-- Q21: Shipping mode performance analysis
SELECT sm.ship_mode_name, sm.speed_tier,
       COUNT(*)                              AS order_lines,
       ROUND(AVG(f.ship_lag_days), 2)        AS avg_lag_days,
       ROUND(SUM(f.sales_amount), 2)         AS total_sales,
       ROUND(SUM(f.profit),       2)         AS total_profit
FROM dw.fact_sales f JOIN dw.dim_ship_mode sm USING (ship_mode_key)
GROUP BY sm.ship_mode_name, sm.speed_tier ORDER BY avg_lag_days;

-- Q22: Sub-category profitability ranking
SELECT p.category, p.sub_category,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct,
       RANK() OVER (PARTITION BY p.category ORDER BY SUM(f.profit) DESC) AS profit_rank
FROM dw.fact_sales f JOIN dw.dim_product p USING (product_key)
GROUP BY p.category, p.sub_category ORDER BY p.category, profit_rank;

-- Q23: Customer retention – orders per customer (loyalty buckets)
WITH customer_orders AS (
  SELECT c.customer_id, c.customer_name, c.segment,
         COUNT(DISTINCT f.order_id) AS order_count
  FROM dw.fact_sales f JOIN dw.dim_customer c USING (customer_key)
  GROUP BY c.customer_id, c.customer_name, c.segment
)
SELECT CASE
         WHEN order_count = 1  THEN '1 - One-time'
         WHEN order_count <= 3 THEN '2 - Occasional (2-3)'
         WHEN order_count <= 6 THEN '3 - Regular (4-6)'
         ELSE                       '4 - Loyal (7+)'
       END AS loyalty_tier,
       COUNT(*) AS customers,
       ROUND(AVG(order_count), 2) AS avg_orders
FROM customer_orders
GROUP BY loyalty_tier ORDER BY loyalty_tier;

-- Q24: Fiscal quarter KPI summary
SELECT d.fiscal_quarter,
       COUNT(DISTINCT f.order_id)    AS total_orders,
       SUM(f.quantity)               AS units_sold,
       ROUND(SUM(f.sales_amount), 2) AS total_sales,
       ROUND(SUM(f.profit),       2) AS total_profit,
       ROUND(SUM(f.profit) / NULLIF(SUM(f.sales_amount), 0) * 100, 2) AS margin_pct
FROM dw.fact_sales f JOIN dw.dim_date d USING (date_key)
GROUP BY d.fiscal_quarter ORDER BY d.fiscal_quarter;

-- Q25: Top 10 high-value orders (by total order revenue)
SELECT f.order_id,
       c.customer_name, c.segment,
       d.full_date AS order_date,
       s.state, s.region,
       ROUND(SUM(f.sales_amount), 2) AS order_revenue,
       ROUND(SUM(f.profit),       2) AS order_profit
FROM dw.fact_sales f
JOIN dw.dim_customer c USING (customer_key)
JOIN dw.dim_date     d USING (date_key)
JOIN dw.dim_store    s USING (store_key)
GROUP BY f.order_id, c.customer_name, c.segment, d.full_date, s.state, s.region
ORDER BY order_revenue DESC LIMIT 10;