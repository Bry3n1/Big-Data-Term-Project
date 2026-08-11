import os
import sqlite3
import pandas as pd

def load_database_tables(db_path):
    """Loads all tables from the SQLite database as pandas DataFrames."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found at: {db_path}")
        
    conn = sqlite3.connect(db_path)
    tables = {}
    
    # Get all table names
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [row[0] for row in cursor.fetchall()]
    
    # Load each table
    for name in table_names:
        tables[name] = pd.read_sql_query(f"SELECT * FROM {name};", conn)
        
    conn.close()
    return tables

def load_csv_files(legacy_path, catalog_path):
    """Loads the legacy customers and product catalog CSV files."""
    if not os.path.exists(legacy_path):
        raise FileNotFoundError(f"Legacy customers CSV not found at: {legacy_path}")
    if not os.path.exists(catalog_path):
        raise FileNotFoundError(f"Product catalog CSV not found at: {catalog_path}")
        
    df_legacy = pd.read_csv(legacy_path)
    df_catalog = pd.read_csv(catalog_path)
    
    return df_legacy, df_catalog

def load_all_raw_data(data_dir):
    """Loads all database tables and CSV datasets."""
    db_path = os.path.join(data_dir, "raw", "ecommerce.db")
    legacy_path = os.path.join(data_dir, "raw", "legacy_customers_export.csv")
    catalog_path = os.path.join(data_dir, "raw", "product_catalog_2024.csv")
    
    db_tables = load_database_tables(db_path)
    df_legacy, df_catalog = load_csv_files(legacy_path, catalog_path)
    
    return db_tables, df_legacy, df_catalog
