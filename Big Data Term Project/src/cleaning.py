import os
import numpy as np
import pandas as pd
from data_loading import load_all_raw_data

def standardize_legacy_dates(df_legacy):
    """
    Standardizes the legacy customer signup dates.
    Identifies and documents four different date formats.
    """
    # Create copy
    df = df_legacy.copy()
    
    # We clean whitespace in column names first
    df.columns = df.columns.str.strip()
    
    # Custom parsing to check formats and log them
    def parse_single_date(date_str):
        if pd.isna(date_str) or str(date_str).strip() == '':
            return pd.NaT
        date_str = str(date_str).strip()
        
        # Formats to try
        formats = [
            ('%Y-%m-%d', 'YYYY-MM-DD'),
            ('%d-%b-%Y', 'DD-Mon-YYYY'),
            ('%B %d, %Y', 'Month DD, YYYY'),
            ('%m/%d/%Y', 'MM/DD/YYYY')
        ]
        
        for fmt, name in formats:
            try:
                val = pd.to_datetime(date_str, format=fmt)
                return val
            except ValueError:
                continue
        # If all fail, return NaT
        return pd.NaT
        
    # Apply parser
    df['signup_date_clean'] = df['Signup_Dt'].apply(parse_single_date)
    return df

def clean_and_reconcile_customers(db_tables, df_legacy):
    """
    Performs Phase 2 Tasks:
    - Normalizes legacy names, emails, and cities
    - Standardizes date formats
    - Resolves customer duplicates & near-duplicates
    - Imputes missing age and flags missing city/gender
    - Integrates Marketing Segment from legacy CRM
    """
    df_db_cust = db_tables['customers'].copy()
    
    # 1. Clean legacy customers first
    df_legacy_clean = df_legacy.copy()
    df_legacy_clean.columns = df_legacy_clean.columns.str.strip()
    
    # Drop completely blank/null rows in legacy (e.g. index 390 is empty)
    df_legacy_clean = df_legacy_clean.dropna(how='all')
    
    # Remove test accounts (e.g., TEST ACCOUNT, test@test.com)
    df_legacy_clean = df_legacy_clean[
        ~df_legacy_clean['Customer Name'].str.lower().str.contains('test', na=True) & 
        ~df_legacy_clean['EMAIL_ADDR'].str.lower().str.contains('test', na=True)
    ]
    
    # Standardize legacy formats
    df_legacy_clean = standardize_legacy_dates(df_legacy_clean)
    
    # String normalization for legacy
    df_legacy_clean['Customer Name'] = df_legacy_clean['Customer Name'].str.strip().str.title()
    df_legacy_clean['EMAIL_ADDR'] = df_legacy_clean['EMAIL_ADDR'].str.strip().str.lower()
    df_legacy_clean['Home City'] = df_legacy_clean['Home City'].str.strip().str.title()
    df_legacy_clean['Marketing Segment'] = df_legacy_clean['Marketing Segment'].str.strip().str.upper()
    
    # Remove duplicates from legacy CSV based on email
    # Keep earliest signup date and first non-null marketing segment
    df_legacy_clean = df_legacy_clean.sort_values(by='signup_date_clean')
    df_legacy_dedup = df_legacy_clean.groupby('EMAIL_ADDR').agg({
        'Customer Name': 'first',
        'Home City': 'first',
        'Marketing Segment': 'first',
        'signup_date_clean': 'first'
    }).reset_index()
    
    # 2. Reconcile with DB Customers
    # Normalize DB customer columns
    df_db_cust['email'] = df_db_cust['email'].str.strip().str.lower()
    df_db_cust['name'] = df_db_cust['name'].str.strip().str.title()
    df_db_cust['city'] = df_db_cust['city'].str.strip().str.title()
    df_db_cust['gender'] = df_db_cust['gender'].str.strip().str.title()
    df_db_cust['signup_date'] = pd.to_datetime(df_db_cust['signup_date'])
    
    # Merge legacy CRM data (Marketing Segment) into DB Customers
    # Left join on email
    df_merged_cust = pd.merge(
        df_db_cust, 
        df_legacy_dedup[['EMAIL_ADDR', 'Marketing Segment']], 
        left_on='email', 
        right_on='EMAIL_ADDR', 
        how='left'
    )
    df_merged_cust = df_merged_cust.drop(columns=['EMAIL_ADDR'])
    df_merged_cust = df_merged_cust.rename(columns={'Marketing Segment': 'marketing_segment'})
    
    # Imputation and missing values policy
    # - marketing_segment: set to 'STANDARD' for customers not in the legacy marketing CRM
    df_merged_cust['marketing_segment'] = df_merged_cust['marketing_segment'].fillna('STANDARD')
    
    # - age: Impute missing age with the overall median age of customers
    median_age = int(df_merged_cust['age'].median())
    df_merged_cust['age'] = df_merged_cust['age'].fillna(median_age).astype(int)
    
    # - city: Replace missing city with 'Unknown'
    df_merged_cust['city'] = df_merged_cust['city'].fillna('Unknown')
    
    # - gender: Replace missing gender with 'Not Specified'
    df_merged_cust['gender'] = df_merged_cust['gender'].fillna('Not Specified')
    
    return df_merged_cust

def clean_products_and_catalog(db_tables, df_catalog):
    """
    Performs Phase 2 Tasks:
    - Identifies extreme price outliers in products using IQR and caps them in-place
    - Integrates external product catalog
    - Reconciles category/dept names
    - Reports overlapping and source-only SKUs
    """
    df_products = db_tables['products'].copy()
    df_cat = df_catalog.copy()
    
    # Clean string columns
    df_products['name'] = df_products['name'].str.strip()
    df_products['category'] = df_products['category'].str.strip()
    df_products['subcategory'] = df_products['subcategory'].str.strip()
    
    df_cat['item_name'] = df_cat['item_name'].str.strip()
    df_cat['dept'] = df_cat['dept'].str.strip()
    
    # 1. Price Outliers detection and capping
    # Global unit_price IQR
    Q1 = df_products['unit_price'].quantile(0.25)
    Q3 = df_products['unit_price'].quantile(0.75)
    IQR = Q3 - Q1
    upper_fence = Q3 + 1.5 * IQR
    lower_fence = Q1 - 1.5 * IQR
    
    outliers = df_products[df_products['unit_price'] > upper_fence]
    num_outliers = len(outliers)
    
    # Cap the outliers at upper_fence in-place
    outliers_log = outliers.copy()
    df_products['unit_price'] = np.where(
        df_products['unit_price'] > upper_fence,
        upper_fence,
        df_products['unit_price']
    )
    
    # 2. Product Catalog Overlap Check
    db_skus = set(df_products['product_id'])
    cat_skus = set(df_cat['SKU'])
    
    overlap = db_skus.intersection(cat_skus)
    db_only = db_skus - cat_skus
    cat_only = cat_skus - db_skus
    
    # Log overlap stats
    overlap_stats = {
        'total_db_products': len(db_skus),
        'total_catalog_products': len(cat_skus),
        'overlap_count': len(overlap),
        'db_only_count': len(db_only),
        'catalog_only_count': len(cat_only)
    }
    
    # 3. Integrate stock levels from catalog into products
    df_products_integrated = pd.merge(
        df_products,
        df_cat[['SKU', 'in_stock_units']],
        left_on='product_id',
        right_on='SKU',
        how='left'
    )
    df_products_integrated = df_products_integrated.drop(columns=['SKU'])
    
    # Impute missing stock levels for database-only products with the median stock of the catalog
    median_stock = int(df_cat['in_stock_units'].median())
    df_products_integrated['in_stock_units'] = df_products_integrated['in_stock_units'].fillna(median_stock).astype(int)
    
    return df_products_integrated, outliers_log, upper_fence, overlap_stats, cat_only

def clean_order_items(db_tables, df_products_cleaned):
    """
    Performs Phase 2 Tasks:
    - Removes exact duplicate order items rows
    - Reconciles transaction prices with capped product unit prices (especially for the outliers)
    - Validates returns (negative quantities)
    """
    df_oi = db_tables['order_items'].copy()
    
    rows_before = len(df_oi)
    
    # Drop exact duplicates
    dup_cols = ['order_id', 'product_id', 'quantity', 'unit_price', 'discount']
    df_oi_dedup = df_oi.drop_duplicates(subset=dup_cols, keep='first').copy()
    
    # Reconcile transaction prices with product unit prices (especially for the outliers)
    # If the product's unit_price in df_products_cleaned was capped, we update the transaction price here to match
    df_merged = pd.merge(df_oi_dedup, df_products_cleaned[['product_id', 'unit_price']], on='product_id', suffixes=('', '_prod'))
    
    # If the transaction price is higher than the capped product price, we cap it
    df_merged['unit_price'] = np.where(
        df_merged['unit_price'] > df_merged['unit_price_prod'],
        df_merged['unit_price_prod'],
        df_merged['unit_price']
    )
    
    df_oi_cleaned = df_merged.drop(columns=['unit_price_prod'])
    
    rows_after = len(df_oi_cleaned)
    num_duplicates = rows_before - rows_after
    
    dedup_stats = {
        'rows_before': rows_before,
        'rows_after': rows_after,
        'duplicates_removed': num_duplicates
    }
    
    return df_oi_cleaned, dedup_stats

def clean_reviews(db_tables):
    """
    Performs Phase 2 Tasks:
    - Corrects out-of-range review ratings (clamps 6 to 5, drops -1 and 0)
    - Fills missing review text with an empty string
    """
    df_reviews = db_tables['reviews'].copy()
    
    # Fix ratings
    invalid_ratings = df_reviews[~df_reviews['rating'].between(1, 5)]
    
    # Clamp 6 to 5
    df_reviews['rating'] = np.where(df_reviews['rating'] == 6, 5, df_reviews['rating'])
    
    # Drop -1 and 0
    df_reviews = df_reviews[df_reviews['rating'].between(1, 5)]
    
    # Fill missing review_text with empty string
    df_reviews['review_text'] = df_reviews['review_text'].fillna('')
    
    return df_reviews, len(invalid_ratings)

def reshape_data_matrix(df_orders, df_order_items, df_products):
    """
    Performs Phase 2 Task:
    - Reshapes data using pivot_table: Category x Month Revenue Matrix
    """
    # Merge order_items, orders, and products
    df_merged = pd.merge(df_order_items, df_orders, on='order_id')
    df_merged = pd.merge(df_merged, df_products, on='product_id', suffixes=('', '_prod'))
    
    # Filter for completed/returned
    df_merged = df_merged[df_merged['status'].isin(['completed', 'returned'])]
    
    # Extract order month
    df_merged['order_month'] = pd.to_datetime(df_merged['order_date']).dt.to_period('M')
    
    # Calculate item revenue: quantity * unit_price * (1 - discount)
    df_merged['net_item_revenue'] = df_merged['quantity'] * df_merged['unit_price'] * (1 - df_merged['discount'])
    
    # Create pivot table
    pivot_matrix = df_merged.pivot_table(
        values='net_item_revenue',
        index='category',
        columns='order_month',
        aggfunc='sum'
    ).fillna(0)
    
    return pivot_matrix

def run_cleaning_pipeline(data_dir):
    """Runs the full cleaning pipeline and saves datasets to processed/ folder."""
    db_tables, df_legacy, df_catalog = load_all_raw_data(data_dir)
    
    # 1. Clean Customers
    df_clean_cust = clean_and_reconcile_customers(db_tables, df_legacy)
    
    # 2. Clean Products
    df_clean_prod, outliers_log, upper_fence, overlap_stats, cat_only = clean_products_and_catalog(db_tables, df_catalog)
    
    # 3. Clean Order Items (passing cleaned products to cap outliers in order items as well)
    df_clean_oi, dedup_stats = clean_order_items(db_tables, df_clean_prod)
    
    # 4. Clean Reviews
    df_clean_rev, num_invalid_ratings = clean_reviews(db_tables)
    
    # 5. Clean Orders
    df_clean_orders = db_tables['orders'].copy()
    df_clean_orders['order_date'] = pd.to_datetime(df_clean_orders['order_date'])
    
    # 6. Clean Web Sessions
    df_clean_ws = db_tables['web_sessions'].copy()
    df_clean_ws['session_date'] = pd.to_datetime(df_clean_ws['session_date'])
    
    # Create category-month revenue matrix (reshaping)
    pivot_matrix = reshape_data_matrix(df_clean_orders, df_clean_oi, df_clean_prod)
    
    # Save datasets
    processed_dir = os.path.join(data_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    
    df_clean_cust.to_csv(os.path.join(processed_dir, "clean_customers.csv"), index=False)
    df_clean_prod.to_csv(os.path.join(processed_dir, "clean_products.csv"), index=False)
    df_clean_orders.to_csv(os.path.join(processed_dir, "clean_orders.csv"), index=False)
    df_clean_oi.to_csv(os.path.join(processed_dir, "clean_order_items.csv"), index=False)
    df_clean_rev.to_csv(os.path.join(processed_dir, "clean_reviews.csv"), index=False)
    df_clean_ws.to_csv(os.path.join(processed_dir, "clean_web_sessions.csv"), index=False)
    
    # Save the reshaped matrix
    pivot_matrix.to_csv(os.path.join(processed_dir, "category_month_revenue_matrix.csv"))
    
    print("--- Phase 2 Cleaning Finished ---")
    print(f"Cleaned Customers shape: {df_clean_cust.shape}")
    print(f"Cleaned Products shape: {df_clean_prod.shape}")
    print(f"Cleaned Order Items shape: {df_clean_oi.shape}")
    print(f"Cleaned Orders shape: {df_clean_orders.shape}")
    print(f"Cleaned Reviews shape: {df_clean_rev.shape}")
    print(f"Cleaned Web Sessions shape: {df_clean_ws.shape}")
    
    # Return stats for reports
    return {
        'outliers_count': len(outliers_log),
        'outliers_fence': upper_fence,
        'outliers': outliers_log,
        'overlap_stats': overlap_stats,
        'supplier_only': cat_only,
        'dedup_stats': dedup_stats,
        'invalid_ratings_count': num_invalid_ratings
    }

if __name__ == "__main__":
    workspace = r"c:\Users\pathp\OneDrive\Desktop\Big Data Term Project"
    stats = run_cleaning_pipeline(os.path.join(workspace, "data"))
    print("\nCleaning Statistics:")
    print(f"Price Outliers Capped: {stats['outliers_count']} (Fence: {stats['outliers_fence']:.2f})")
    print(f"Order Item Duplicates Removed: {stats['dedup_stats']['duplicates_removed']}")
    print(f"Out-of-range Review Ratings corrected: {stats['invalid_ratings_count']}")
    print(f"Catalog Overlap: {stats['overlap_stats']}")
