# UrbanCart Dataset — Data Dictionary

## SQLite database: `ecommerce.db`

### customers
| column | type | notes |
|---|---|---|
| customer_id | INTEGER PK | |
| name | TEXT | |
| email | TEXT | unique |
| signup_date | TEXT (YYYY-MM-DD) | |
| city | TEXT | ~3% missing |
| country | TEXT | |
| age | INTEGER | ~6% missing |
| gender | TEXT | F / M / Other / missing |

### products
| column | type | notes |
|---|---|---|
| product_id | INTEGER PK | |
| name | TEXT | |
| category | TEXT | 6 categories |
| subcategory | TEXT | |
| unit_price | REAL | ~1% extreme outliers (data entry errors) |
| cost | REAL | |

### orders
| column | type | notes |
|---|---|---|
| order_id | INTEGER PK | |
| customer_id | INTEGER FK -> customers | |
| order_date | TEXT (YYYY-MM-DD HH:MM:SS) | |
| status | TEXT | completed / returned / cancelled / pending |
| payment_method | TEXT | |

### order_items
| column | type | notes |
|---|---|---|
| order_item_id | INTEGER PK | |
| order_id | INTEGER FK -> orders | |
| product_id | INTEGER FK -> products | |
| quantity | INTEGER | negative values represent returns |
| unit_price | REAL | price at time of order |
| discount | REAL | fraction, e.g. 0.10 = 10% off |
| — | | ~0.8% exact-duplicate rows (data entry errors) |

### reviews
| column | type | notes |
|---|---|---|
| review_id | INTEGER PK | |
| product_id | INTEGER FK -> products | |
| customer_id | INTEGER FK -> customers | |
| rating | INTEGER | should be 1-5; a few out-of-range values exist |
| review_date | TEXT (YYYY-MM-DD) | |
| review_text | TEXT | ~20% missing |

### web_sessions
| column | type | notes |
|---|---|---|
| session_id | INTEGER PK | |
| customer_id | INTEGER FK -> customers | |
| session_date | TEXT (YYYY-MM-DD HH:MM:SS) | |
| device | TEXT | mobile / desktop / tablet |
| duration_minutes | REAL | |
| pages_viewed | INTEGER | |

## External files (NOT in the database — must be loaded and reconciled with pandas)

### legacy_customers_export.csv
An old marketing-system export of customer signups. Deliberately messy:
inconsistent date formats across rows, inconsistent name casing, stray
whitespace in headers/values, some duplicated/near-duplicate customers,
some missing emails, and a couple of junk rows (test accounts, blank rows).

### product_catalog_2024.csv
A supplier-provided product catalog with different column names/casing
than the `products` table, partial overlap in coverage, and a handful of
supplier-only SKUs that do not exist in the internal database at all.
