# Warehouse Setup Guide

## Prerequisites
- Python 3.10+
- PostgreSQL-compatible database access
- Supabase project or another PostgreSQL instance
- Access to the project folder

## 1. Create a virtual environment
From the project root:

```bash
python -m venv venv
```

Activate it:

- Windows PowerShell:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

- Bash:
  ```bash
  source venv/Scripts/activate
  ```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment variables
Create a local file named `.env` in the project root.

Use the example file `.env.example` as a template.

Example configuration:

```ini
DB_HOST=aws-0-ap-south-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.your_project_ref
DB_PASSWORD=YourDatabasePassword
DB_URL=postgresql+psycopg2://postgres.your_project_ref:YourDatabasePassword@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
```

Important notes:
- For Supabase pooler connections, use port 5432
- Keep `sslmode=require` in the SQLAlchemy URL
- Ensure the database name actually exists in the target Supabase project

## 4. Run the project
From the root folder:

```bash
python main.py
```

## 5. Recommended execution order
Use the interactive menu in this order:
1. Check database connection
2. Create warehouse schemas and tables
3. Load staging orders
4. Load reference data
5. Build the warehouse
6. Run queries
7. Generate reports

## 6. Troubleshooting
If the project fails to connect:
- confirm `.env` values are correct
- check that `DB_NAME` exists in the database
- verify the Supabase user and password are valid
- ensure the connection has internet access and SSL is enabled

## 7. Security notes
- Never commit `.env` to source control
- Keep secrets out of project files and logs
- Use environment variables or a secure secret manager in production
