# UrbanCart Big Data Analytics & Engineering Pipeline

This repository contains the complete analytics pipeline for the university term project **UrbanCart Big Data**. It processes raw databases and marketing sheets, integrates them, executes statistical models, generates business visualizations, and compiles a comprehensive executive report.

## Project Structure

```
UrbanCart-Big-Data-Project/
├── data/
│   ├── raw/
│   │   ├── ecommerce.db                 # Raw transactional SQLite database
│   │   ├── legacy_customers_export.csv  # Messy legacy customer signup export
│   │   └── product_catalog_2024.csv     # Supplier inventory and catalog details
│   └── processed/
│       ├── clean_customers.csv          # Reconciled, deduplicated customer master
│       ├── clean_products.csv           # Capped product price catalog with stock
│       ├── clean_orders.csv             # Standardized order table
│       ├── clean_order_items.csv        # Deduplicated transaction items with returns
│       ├── clean_reviews.csv            # Cleaned product reviews directory
│       ├── clean_web_sessions.csv       # Cleaned browsing sessions database
│       └── category_month_revenue_matrix.csv # Reshaped monthly sales matrix
├── sql/
│   └── queries.sql                      # 10 core analytical SQL queries
├── notebooks/
│   └── analysis.ipynb                   # Jupyter notebook driver for Phase 4
├── src/
│   ├── data_loading.py                  # Module for database and CSV loaders
│   ├── cleaning.py                      # Reconcile, clean, and deduplicate data
│   ├── numpy_analysis.py                # Raw NumPy implementations of analytical models
│   ├── visualizations.py                # Generation scripts for matplotlib/seaborn charts
│   └── pipeline.py                      # Main executable driver for end-to-end runs
├── figures/                             # Generated charts and visualizations (PNG)
│   └── chart_1_rfm_revenue.png etc.
├── report/
│   ├── report.pdf                       # Final 54-page PDF document
│   └── executive_summary.pdf            # Standalone executive summary page
├── requirements.txt                     # Dependencies listing
└── README.md                            # Project documentation
```

## Running the Pipeline

To execute the entire data pipeline from raw files to final figures and reports, run the following:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Pipeline**:
   ```bash
   python src/pipeline.py
   ```
   *Note: This cleans the data, runs the RFM segmentation, collaborative recommendations, Normal equation regression, Monte Carlo stockout simulation, and creates the charts.*

3. **Generate Reports**:
   ```bash
   python src/generate_report.py
   ```

4. **Interactive Analysis**:
   Open `notebooks/analysis.ipynb` in Jupyter Notebook or VS Code to run interactive cells and view embedded visualizations.

## Key Statistical Findings

* **RFM Champions Core**: 16.3% of the customer base ('Champions') accounts for over 50% ($5.39M) of total net spend.
* **Consistent Revenue Expansion**: Monthly sales expanded from $176k to over $302k over the 24-month horizon. A linear model fits this growth with $R^2 = 84.93\%$, projecting January 2025 sales at $311.6k.
* **Profit Margin Profiles**: Books & Media exhibits the highest effective profit margin (50.1%), while Electronics has the lowest margin (38.6%) due to return rates.
* **Supply Chain Safety**: Safety stock limits calculated via Monte Carlo simulations indicate reorder points should trigger at 7.3 units for product 136 (Watch Footwear) to maintain a stockout risk under 5%.

## Team Contribution Statement

This project was developed by a team 4 people include.
1. Path Pisoth       ID: CSE2024190005
2. Vong Sokraksa     ID: CSE2024190001
3. Thou Soengvisal   ID: CSE2024190021
4. Sun Sothy         ID: CSE2024190041 
* **100% of Effort**: Data extraction (SQL), loading and preprocessing (Pandas), numerical modeling (NumPy), chart generation (Matplotlib/Seaborn), and technical writing (ReportLab).

