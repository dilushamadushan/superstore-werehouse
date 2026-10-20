import os
import sys
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import quote_plus
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_ENGINE: Engine | None = None

def get_db_url() -> str:
    db_url = os.getenv("DB_URL")
    if db_url:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return db_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")

    encoded_user = quote_plus(user)
    encoded_password = quote_plus(password)

    return (
        f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{host}:{port}/{dbname}"
        f"?sslmode=require"
    )


def get_engine(pool_size: int = 5, max_overflow: int = 10, **kwargs) -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = get_db_url()
        _ENGINE = create_engine(
            url,
            pool_pre_ping=True,  
            pool_size=pool_size,
            max_overflow=max_overflow,
            **kwargs,
        )
    return _ENGINE


@contextmanager
def get_connection():
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


@contextmanager
def get_raw_connection():
    host = os.getenv("DB_HOST")
    port = int(os.getenv("DB_PORT", "5432"))
    dbname = os.getenv("DB_NAME", "postgres")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        sslmode="require",
        connect_timeout=15,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def test_connection_health() -> tuple[bool, str]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            ver = conn.execute(text("SELECT version();")).scalar()
            return True, str(ver)
    except Exception as e:
        return False, str(e)


def execute_sql_file(file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(f"SQL file not found at: {path}")

    sql_content = path.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.execute(text(sql_content))
    print(f"[SUCCESS] Executed SQL file: {path.name}")


def truncate_all_warehouse_tables() -> list[str]:
    engine = get_engine()
    with engine.connect() as conn:
        tables = conn.execute(
            text(
                """
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema IN ('staging', 'dw') AND table_type = 'BASE TABLE';
                """
            )
        ).fetchall()

    if not tables:
        return []

    table_names = [f'"{s}"."{t}"' for s, t in tables]
    truncate_stmt = f"TRUNCATE TABLE {', '.join(table_names)} CASCADE;"
    
    with engine.begin() as conn:
        conn.execute(text(truncate_stmt))

    return [f"{s}.{t}" for s, t in tables]


def drop_warehouse_schemas() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS staging CASCADE;"))
        conn.execute(text("DROP SCHEMA IF EXISTS dw CASCADE;"))
    print("[SUCCESS] Schemas 'staging' and 'dw' dropped completely.")


if __name__ == "__main__":
    ok, msg = test_connection_health()
    if ok:
        print("Connected! PostgreSQL Version:\n", msg)
    else:
        print("Connection failed:\n", msg)
