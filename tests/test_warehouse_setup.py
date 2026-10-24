import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.db import validate_db_config
from scripts.run_queries import load_queries
from scripts.quality_checks import validate_staging_dataframe


class TestWarehouseSetup(unittest.TestCase):
    def test_db_config_validation_accepts_required_fields(self):
        config = {
            "DB_HOST": "aws-0-ap-south-1.pooler.supabase.com",
            "DB_PORT": "5432",
            "DB_NAME": "postgres",
            "DB_USER": "postgres.user",
            "DB_PASSWORD": "secret",
        }
        self.assertIsNone(validate_db_config(config))

    def test_db_config_validation_requires_missing_fields(self):
        config = {
            "DB_HOST": "aws-0-ap-south-1.pooler.supabase.com",
            "DB_PORT": "5432",
            "DB_NAME": "postgres",
        }
        with self.assertRaises(ValueError):
            validate_db_config(config)

    def test_queries_file_has_25_queries(self):
        queries = load_queries()
        self.assertEqual(len(queries), 25)

    def test_validate_staging_dataframe_accepts_valid_data(self):
        df = {
            "row_id": [1, 2],
            "order_id": ["A-1", "A-2"],
            "order_date": ["2024-01-01", "2024-01-02"],
            "ship_date": ["2024-01-03", "2024-01-04"],
            "ship_mode": ["Standard Class", "First Class"],
            "customer_id": ["C1", "C2"],
            "customer_name": ["John", "Alice"],
            "segment": ["Consumer", "Corporate"],
            "country": ["United States", "United States"],
            "city": ["Los Angeles", "New York"],
            "state": ["California", "New York"],
            "postal_code": ["90001", "10001"],
            "region": ["West", "East"],
            "product_id": ["P1", "P2"],
            "category": ["Furniture", "Technology"],
            "sub_category": ["Chairs", "Phones"],
            "product_name": ["Chair", "Phone"],
            "sales": [100.0, 200.0],
            "quantity": [1, 2],
            "discount": [0.1, 0.2],
            "profit": [10.0, 20.0],
        }
        validate_staging_dataframe(df)

    def test_validate_staging_dataframe_rejects_missing_required_columns(self):
        df = {
            "order_id": ["A-1"],
            "order_date": ["2024-01-01"],
        }
        with self.assertRaises(ValueError):
            validate_staging_dataframe(df)

    def test_validate_staging_dataframe_rejects_duplicate_row_ids(self):
        df = {
            "row_id": [1, 1],
            "order_id": ["A-1", "A-1"],
            "order_date": ["2024-01-01", "2024-01-01"],
            "ship_date": ["2024-01-03", "2024-01-03"],
            "ship_mode": ["Standard Class", "Standard Class"],
            "customer_id": ["C1", "C1"],
            "customer_name": ["John", "John"],
            "segment": ["Consumer", "Consumer"],
            "country": ["United States", "United States"],
            "city": ["Los Angeles", "Los Angeles"],
            "state": ["California", "California"],
            "postal_code": ["90001", "90001"],
            "region": ["West", "West"],
            "product_id": ["P1", "P2"],
            "category": ["Furniture", "Furniture"],
            "sub_category": ["Chairs", "Tables"],
            "product_name": ["Chair", "Table"],
            "sales": [100.0, 200.0],
            "quantity": [1, 2],
            "discount": [0.1, 0.2],
            "profit": [10.0, 20.0],
        }
        with self.assertRaises(ValueError):
            validate_staging_dataframe(df)

    def test_report_excel_contains_query_results_sheet(self):
        from scripts.report_excel import generate_excel_report
        from openpyxl import load_workbook

        report_path = ROOT / "reports" / "test_query_results.xlsx"
        df = {
            "Q1": pd.DataFrame({"Year No": [2014], "Total Sales": [100.0]}),
            "Q2": pd.DataFrame({"Year No": [2014], "Total Sales": [90.0]})
        }

        generate_excel_report(report_path, {"total_revenue": 100.0}, df, "20261024_120000", queries_catalog=[("Q1", "Test Query 1", ""), ("Q2", "Test Query 2", "")])
        workbook = load_workbook(report_path)
        self.assertIn("Query Results", workbook.sheetnames)
        self.assertIn("All Queries", workbook.sheetnames)


if __name__ == "__main__":
    unittest.main()
