# Superstore Warehouse Project Overview

## Purpose
The project implements an end-to-end warehouse solution for a retail sales dataset. It transforms raw transactional data into a dimensional model that supports reporting, analysis, and business decision-making.

## Business goal
The warehouse helps answer business questions such as:
- Which products are driving revenue and profit?
- Which customers and regions are most valuable?
- How do promotions affect sales and profitability?
- What are the seasonal and holiday patterns in revenue?
- How is shipping performance affecting operations?

## Architecture
The solution follows a classic staged warehouse architecture:

1. Source layer
   - CSV dataset for retail orders
   - External holiday data
   - Derived store and promotion reference data

2. Staging layer
   - Raw data is loaded into staging tables for validation and transformation
   - Tables include orders, holidays, stores, and promotions

3. Warehouse layer
   - The dw schema contains dimensions and a fact table
   - The design follows a star schema pattern

4. Analytics layer
   - SQL business queries are executed against the warehouse
   - Outputs are saved as CSV and report files

## Core warehouse design
The warehouse includes:
- dw.dim_date
- dw.dim_product
- dw.dim_customer
- dw.dim_store
- dw.dim_promo
- dw.dim_ship_mode
- dw.fact_sales

This structure supports analytical queries and allows different business dimensions to be sliced and aggregated.

## Data flow
The typical flow is:
1. Validate database configuration
2. Create schemas in PostgreSQL
3. Load raw sales data into staging
4. Load holiday, store, and promotion reference data
5. Transform data into the star schema
6. Execute BI queries
7. Generate Excel and HTML reports

## Technologies used
- Python
- PostgreSQL / Supabase
- SQLAlchemy
- Pandas
- psycopg2-binary
- python-dotenv

## Current project status
The project is a strong warehouse-style implementation for a learning, demo, or portfolio environment. It already includes the main building blocks of a data warehouse:
- staging layer
- dimensional modeling
- analytical SQL
- reporting
- CLI-based execution

## Gaps to improve
The system can be upgraded for stronger production reliability through:
- more robust data validation
- better testing coverage
- clearer project documentation
- stronger ETL logging and error handling
- optional incremental loading and deployment improvements
