import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style globally for premium aesthetics
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.color'] = '#333333'
plt.rcParams['ytick.color'] = '#333333'
plt.rcParams['grid.color'] = '#EEEEEE'
plt.rcParams['grid.linewidth'] = 0.5

# Curated premium color palette
colors = {
    'primary': '#1A365D',      # Deep Navy
    'secondary': '#2B6CB0',    # Muted Blue
    'accent': '#319795',       # Teal
    'highlight': '#DD6B20',    # Warm Amber/Orange
    'danger': '#E53E3E',       # Crimson Red
    'background': '#F7FAFC',   # Soft Gray
    'text': '#2D3748'          # Charcoal
}

def generate_chart_1_rfm(processed_dir, fig_dir):
    """
    Chart 1: RFM Segment Revenue Contribution.
    """
    df_rfm = pd.read_csv(os.path.join(processed_dir, "customer_rfm_scores.csv"))
    
    # Calculate revenue and count per segment
    segment_stats = df_rfm.groupby('rfm_segment').agg({
        'monetary': 'sum',
        'recency': 'count'
    }).rename(columns={'recency': 'customer_count'}).reset_index()
    
    segment_stats = segment_stats.sort_values(by='monetary', ascending=True)
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    bars = ax.barh(segment_stats['rfm_segment'], segment_stats['monetary'] / 1e3, 
                   color=[colors['secondary'], colors['accent'], '#4A5568', colors['primary'], colors['highlight']], 
                   edgecolor='none', height=0.6)
    
    # Add values on bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 20, bar.get_y() + bar.get_height()/2, f"${width:.1f}k", 
                va='center', ha='left', fontsize=10, fontweight='bold', color=colors['text'])
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    
    ax.xaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Revenue Contribution by RFM Segment ($ Thousands)", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_xlabel("Total Net Spend ($k)", fontsize=11, labelpad=10, color=colors['text'])
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_1_rfm_revenue.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_2_seasonality(processed_dir, fig_dir):
    """
    Chart 2: MoM Revenue Trend and Seasonality.
    """
    df_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    df_oi = pd.read_csv(os.path.join(processed_dir, "clean_order_items.csv"))
    
    df_sales = pd.merge(df_oi, df_orders, on='order_id')
    df_sales = df_sales[df_sales['status'].isin(['completed', 'returned'])]
    df_sales['net_revenue'] = df_sales['quantity'] * df_sales['unit_price'] * (1 - df_sales['discount'])
    
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
    df_monthly = df_sales.groupby(df_sales['order_date'].dt.to_period('M'))['net_revenue'].sum().reset_index()
    df_monthly['order_month'] = df_monthly['order_date'].dt.strftime('%Y-%m')
    df_monthly = df_monthly.sort_values(by='order_month')
    
    # Calculate rolling 3-month average
    df_monthly['rolling_avg'] = df_monthly['net_revenue'].rolling(window=3, min_periods=1).mean()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    # Plot bars for monthly revenue
    ax.bar(df_monthly['order_month'], df_monthly['net_revenue'] / 1e3, color='#CBD5E0', width=0.6, label='Monthly Revenue')
    
    # Plot line for trend
    ax.plot(df_monthly['order_month'], df_monthly['rolling_avg'] / 1e3, color=colors['primary'], linewidth=2.5, 
            marker='o', label='3-Month Rolling Average')
    
    # Highlight highest and lowest revenue months
    max_idx = df_monthly['net_revenue'].idxmax()
    min_idx = df_monthly['net_revenue'].idxmin()
    
    ax.annotate(f"Peak: ${df_monthly.loc[max_idx, 'net_revenue']/1e3:.1f}k", 
                xy=(df_monthly.loc[max_idx, 'order_month'], df_monthly.loc[max_idx, 'net_revenue']/1e3),
                xytext=(df_monthly.loc[max_idx, 'order_month'], df_monthly.loc[max_idx, 'net_revenue']/1e3 + 20),
                arrowprops=dict(facecolor=colors['accent'], arrowstyle="->", connectionstyle="arc3,rad=.2"),
                fontsize=10, fontweight='bold', color=colors['accent'])
                
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    plt.xticks(rotation=45, ha='right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Month-over-Month Revenue Trend (2022 - 2024)", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_ylabel("Revenue ($ Thousands)", fontsize=11, labelpad=10, color=colors['text'])
    ax.legend(frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0')
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_2_monthly_trend.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_3_margins(processed_dir, fig_dir):
    """
    Chart 3: Effective Profit Margin by Category.
    """
    df_oi = pd.read_csv(os.path.join(processed_dir, "clean_order_items.csv"))
    df_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    df_products = pd.read_csv(os.path.join(processed_dir, "clean_products.csv"))
    
    df_merged = pd.merge(df_oi, df_orders, on='order_id')
    df_merged = pd.merge(df_merged, df_products, on='product_id', suffixes=('', '_prod'))
    
    df_merged = df_merged[df_merged['status'].isin(['completed', 'returned'])]
    
    # Net revenue: quantity * price * (1-discount)
    # COGS: quantity * cost (Only for sold items, returns have quantity -1 which correctly reduces COGS)
    df_merged['net_rev'] = df_merged['quantity'] * df_merged['unit_price'] * (1 - df_merged['discount'])
    df_merged['cogs'] = df_merged['quantity'] * df_merged['cost']
    df_merged['profit'] = df_merged['net_rev'] - df_merged['cogs']
    
    cat_margin = df_merged.groupby('category').agg({
        'net_rev': 'sum',
        'profit': 'sum'
    }).reset_index()
    
    cat_margin['margin'] = cat_margin['profit'] / cat_margin['net_rev']
    cat_margin = cat_margin.sort_values(by='margin', ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    bars = ax.bar(cat_margin['category'], cat_margin['margin'] * 100, color=colors['secondary'], width=0.5)
    
    # Add values on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1.5, f"{height:.1f}%", 
                va='bottom', ha='center', fontsize=10, fontweight='bold', color=colors['text'])
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    ax.set_ylim(0, 100)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Effective Profit Margin by Product Category", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_ylabel("Profit Margin (%)", fontsize=11, labelpad=10, color=colors['text'])
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_3_profit_margins.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_4_reviews(processed_dir, fig_dir):
    """
    Chart 4: Review Ratings vs. Repeat Purchase Behavior.
    """
    df_reviews = pd.read_csv(os.path.join(processed_dir, "clean_reviews.csv"))
    df_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    
    # Find active customers and their order counts
    cust_orders = df_orders[df_orders['status'].isin(['completed', 'returned'])].groupby('customer_id')['order_id'].nunique()
    
    # Merge with reviews
    df_rev_cust = pd.merge(df_reviews, cust_orders, on='customer_id', how='inner')
    df_rev_cust['is_repeat'] = df_rev_cust['order_id'] >= 2
    
    # Repeat rate per rating group
    rating_stats = df_rev_cust.groupby('rating')['is_repeat'].mean().reset_index()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    bars = ax.bar(rating_stats['rating'].astype(str), rating_stats['is_repeat'] * 100, color=colors['accent'], width=0.5)
    
    # Add values on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1.5, f"{height:.1f}%", 
                va='bottom', ha='center', fontsize=10, fontweight='bold', color=colors['text'])
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    ax.set_ylim(0, 100)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Customer Repeat Purchase Rate by Review Rating (1 - 5 Stars)", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_ylabel("Repeat Purchase Rate (%)", fontsize=11, labelpad=10, color=colors['text'])
    ax.set_xlabel("Review Rating Given", fontsize=11, labelpad=10, color=colors['text'])
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_4_reviews_repeat_rate.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_5_conversion(processed_dir, fig_dir):
    """
    Chart 5: Device Type & Country Conversion Rate Heatmap.
    """
    df_ws = pd.read_csv(os.path.join(processed_dir, "clean_web_sessions.csv"))
    df_cust = pd.read_csv(os.path.join(processed_dir, "clean_customers.csv"))
    df_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    
    # Merge web sessions with customer country
    df_ws_cust = pd.merge(df_ws, df_cust[['customer_id', 'country']], on='customer_id')
    
    # Total unique sessions per country and device
    session_counts = df_ws_cust.groupby(['country', 'device'])['session_id'].nunique().reset_index(name='sessions')
    
    # Find sessions that resulted in a purchase (sessions where customer has orders on the same day or generally,
    # let's define engaged-to-purchase conversion: purchasing customers / engaged customers)
    # The PDF defines Conversion Rate = Purchasing Customers / Engaged Customers
    # Engaged customers: customers who have at least one web session.
    # Purchasing customers: customers who made a purchase.
    # Let's calculate this ratio split by country and device (device of their session).
    # Group customers by country and device (most frequent device used, or split by session device)
    # Let's find customer-device profiles:
    cust_device_sessions = df_ws_cust.groupby(['customer_id', 'country', 'device']).size().reset_index(name='session_count')
    # Keep the primary device for each customer
    idx = cust_device_sessions.groupby('customer_id')['session_count'].idxmax()
    cust_primary_device = cust_device_sessions.loc[idx]
    
    # Check who made a purchase
    purchasing_custs = set(df_orders[df_orders['status'].isin(['completed', 'returned'])]['customer_id'])
    cust_primary_device['is_purchasing'] = cust_primary_device['customer_id'].isin(purchasing_custs)
    
    # Conversion rate = share of purchasing customers
    conv_data = cust_primary_device.groupby(['country', 'device'])['is_purchasing'].mean().unstack().fillna(0)
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('#FFFFFF')
    
    sns.heatmap(conv_data * 100, annot=True, fmt=".1f", cmap="YlGnBu", linewidths=0.5, ax=ax,
                cbar_kws={'label': 'Conversion Rate (%)'}, annot_kws={'weight': 'bold', 'size': 11})
                
    ax.set_title("Engagement-to-Purchase Conversion Rate (%) by Device & Country", 
                 fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_xlabel("Device Type", fontsize=11, labelpad=10, color=colors['text'])
    ax.set_ylabel("Country", fontsize=11, labelpad=10, color=colors['text'])
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_5_conversion_heatmap.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_6_forecast(processed_dir, fig_dir):
    """
    Chart 6: Revenue Forecasting with Uncertainty Bands.
    """
    df_reg = pd.read_csv(os.path.join(processed_dir, "regression_coefficients.csv"))
    # Load raw regression info via run_linear_regression outputs or files
    # We can reconstruct it from files
    df_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    df_oi = pd.read_csv(os.path.join(processed_dir, "clean_order_items.csv"))
    
    df_sales = pd.merge(df_oi, df_orders, on='order_id')
    df_sales = df_sales[df_sales['status'].isin(['completed', 'returned'])]
    df_sales['net_revenue'] = df_sales['quantity'] * df_sales['unit_price'] * (1 - df_sales['discount'])
    
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
    df_monthly = df_sales.groupby(df_sales['order_date'].dt.to_period('M'))['net_revenue'].sum().reset_index()
    df_monthly['order_month'] = df_monthly['order_date'].dt.strftime('%Y-%m')
    df_monthly = df_monthly.sort_values(by='order_month').tail(24).reset_index(drop=True)
    
    beta_0 = df_reg[df_reg['parameter'].str.contains('intercept')]['coefficient'].values[0]
    beta_1 = df_reg[df_reg['parameter'].str.contains('slope')]['coefficient'].values[0]
    
    # Month indices
    indices = np.arange(1, 27) # 24 historical + 2 forecast
    predicted_revs = beta_0 + beta_1 * indices
    
    # We estimate standard error of forecast (use residual std err as proxy for uncertainty)
    # We know R^2 and predictions. Let's find residual std dev
    y_hist = df_monthly['net_revenue'].to_numpy()
    y_hist_pred = beta_0 + beta_1 * np.arange(1, 25)
    resid_std = np.sqrt(np.sum((y_hist - y_hist_pred)**2) / (len(y_hist) - 2))
    
    # Month labels for plot
    month_labels = df_monthly['order_month'].tolist()
    # Add next two months
    last_year, last_month = map(int, month_labels[-1].split('-'))
    next_months = []
    curr_y, curr_m = last_year, last_month
    for _ in range(2):
        curr_m += 1
        if curr_m > 12:
            curr_m = 1
            curr_y += 1
        next_months.append(f"{curr_y}-{curr_m:02d}")
    all_months = month_labels + next_months
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    # Plot historical
    ax.plot(all_months[:24], y_hist / 1e3, color=colors['secondary'], marker='o', label='Historical Revenue')
    
    # Plot forecast
    ax.plot(all_months[23:], predicted_revs[23:] / 1e3, color=colors['highlight'], linestyle='--', 
            marker='s', linewidth=2.5, label='2-Month Linear Forecast')
    
    # Shaded uncertainty range (95% CI: +/- 1.96 * standard error)
    forecast_err = resid_std * np.sqrt(1 + 1/24 + (indices - np.mean(np.arange(1, 25)))**2 / np.sum((np.arange(1, 25) - 12.5)**2))
    lower_band = (predicted_revs - 1.96 * forecast_err) / 1e3
    upper_band = (predicted_revs + 1.96 * forecast_err) / 1e3
    
    # Shading only forecast period
    ax.fill_between(all_months[23:], lower_band[23:], upper_band[23:], color=colors['highlight'], alpha=0.15, label='95% Forecast Interval')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    plt.xticks(rotation=45, ha='right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Revenue Linear Forecast for Next 2 Months ($ Thousands)", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_ylabel("Revenue ($ Thousands)", fontsize=11, labelpad=10, color=colors['text'])
    ax.legend(frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0')
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_6_revenue_forecast.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_7_monte_carlo(processed_dir, fig_dir):
    """
    Chart 7: Monte Carlo Stockout Demand Distributions.
    """
    df_mc = pd.read_csv(os.path.join(processed_dir, "monte_carlo_stockout_stats.csv"))
    
    # We will simulate and recreate demand distributions for the top 3 products or load them.
    # To avoid re-running simulation, let's draw demand distributions based on saved stats in df_mc
    # We can reconstruct distributions using N(mean, std)
    np.random.seed(42)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    palette = [colors['primary'], colors['accent'], colors['highlight']]
    
    for i, row in df_mc.iterrows():
        mean_30d = row['mean_daily_demand'] * 30
        std_30d = row['std_daily_demand'] * np.sqrt(30)
        
        sim_demand = np.random.normal(mean_30d, std_30d, 5000)
        sim_demand = np.clip(sim_demand, 0, None)
        
        sns.kdeplot(sim_demand, ax=ax, label=f"{row['product_name']}", color=palette[i], fill=True, alpha=0.15, linewidth=2)
        
        # Draw vertical line for recommended reorder point
        ax.axvline(row['reorder_point'], color=palette[i], linestyle='--', alpha=0.8,
                   label=f"{row['product_name']} Reorder Pt: {row['reorder_point']:.1f}")
        
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    ax.xaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Simulated 30-Day Lead Time Demand & Recommended Reorder Points", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_xlabel("Simulated 30-Day Lead Time Demand (Units)", fontsize=11, labelpad=10, color=colors['text'])
    ax.legend(frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0')
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_7_monte_carlo.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_chart_8_data_quality(raw_db_path, processed_dir, fig_dir):
    """
    Chart 8: Data-Quality Business Impact Comparison (Raw vs Cleaned Data).
    Shows how a business conclusion (e.g. top products revenue) changes drastically due to cleaning.
    """
    import sqlite3
    
    # 1. Calculate top products revenue using RAW data
    conn = sqlite3.connect(raw_db_path)
    df_raw_items = pd.read_sql_query("SELECT product_id, quantity, unit_price, discount FROM order_items;", conn)
    df_raw_prods = pd.read_sql_query("SELECT product_id, name FROM products;", conn)
    conn.close()
    
    df_raw_merged = pd.merge(df_raw_items, df_raw_prods, on='product_id')
    df_raw_merged['raw_rev'] = df_raw_merged['quantity'] * df_raw_merged['unit_price'] * (1 - df_raw_merged['discount'])
    raw_prod_rev = df_raw_merged.groupby(['product_id', 'name'])['raw_rev'].sum().reset_index()
    raw_prod_rev = raw_prod_rev.sort_values(by='raw_rev', ascending=False).head(5)
    
    # 2. Calculate cleaned products revenue
    df_clean_items = pd.read_csv(os.path.join(processed_dir, "clean_order_items.csv"))
    df_clean_prods = pd.read_csv(os.path.join(processed_dir, "clean_products.csv"))
    df_clean_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    
    df_clean_merged = pd.merge(df_clean_items, df_clean_orders, on='order_id')
    df_clean_merged = pd.merge(df_clean_merged, df_clean_prods, on='product_id', suffixes=('', '_prod'))
    df_clean_merged = df_clean_merged[df_clean_merged['status'].isin(['completed', 'returned'])]
    df_clean_merged['clean_rev'] = df_clean_merged['quantity'] * df_clean_merged['unit_price'] * (1 - df_clean_merged['discount'])
    
    clean_prod_rev = df_clean_merged.groupby(['product_id', 'name'])['clean_rev'].sum().reset_index()
    # Keep the same 5 products as raw or look at clean top 5
    # Let's compare the raw top 5 to see how their values change after cleaning!
    compared_df = pd.merge(raw_prod_rev, clean_prod_rev, on=['product_id', 'name'], how='left').fillna(0)
    
    # Melt for grouped plotting
    df_plot = pd.melt(compared_df, id_vars=['name'], value_vars=['raw_rev', 'clean_rev'],
                      var_name='Data Type', value_name='Revenue')
    df_plot['Data Type'] = df_plot['Data Type'].map({'raw_rev': 'Raw (Uncleaned)', 'clean_rev': 'Cleaned (Capped & Deduplicated)'})
    
    # Shorten names for plotting
    df_plot['name'] = df_plot['name'].apply(lambda x: x[:20] + '...' if len(x) > 20 else x)
    
    # Grouped Bar Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_facecolor(colors['background'])
    fig.patch.set_facecolor('#FFFFFF')
    
    sns.barplot(data=df_plot, x='name', y=df_plot['Revenue'] / 1e3, hue='Data Type', 
                palette=[colors['danger'], colors['accent']], ax=ax)
                
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    ax.set_title("Material Business Impact of Data Cleaning: Top Product Revenues", fontsize=14, fontweight='bold', pad=20, color=colors['primary'])
    ax.set_ylabel("Revenue ($ Thousands)", fontsize=11, labelpad=10, color=colors['text'])
    ax.set_xlabel("Product Name", fontsize=11, labelpad=10, color=colors['text'])
    ax.legend(frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0')
    
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "chart_8_data_quality_impact.png"), dpi=300, facecolor=fig.get_facecolor())
    plt.close()

def generate_all_charts(data_dir, fig_dir):
    """Runs chart generation for all 8 business insights and logs progress."""
    os.makedirs(fig_dir, exist_ok=True)
    processed_dir = os.path.join(data_dir, "processed")
    raw_db_path = os.path.join(data_dir, "raw", "ecommerce.db")
    
    print("Generating Chart 1 (RFM)...")
    generate_chart_1_rfm(processed_dir, fig_dir)
    
    print("Generating Chart 2 (Monthly trend)...")
    generate_chart_2_seasonality(processed_dir, fig_dir)
    
    print("Generating Chart 3 (Margins)...")
    generate_chart_3_margins(processed_dir, fig_dir)
    
    print("Generating Chart 4 (Reviews repeat rate)...")
    generate_chart_4_reviews(processed_dir, fig_dir)
    
    print("Generating Chart 5 (Conversion heatmap)...")
    generate_chart_5_conversion(processed_dir, fig_dir)
    
    print("Generating Chart 6 (Revenue forecast)...")
    generate_chart_6_forecast(processed_dir, fig_dir)
    
    print("Generating Chart 7 (Monte Carlo KDE)...")
    generate_chart_7_monte_carlo(processed_dir, fig_dir)
    
    print("Generating Chart 8 (Data quality comparisons)...")
    generate_chart_8_data_quality(raw_db_path, processed_dir, fig_dir)
    
    print("--- All Charts Generated Successfully ---")

if __name__ == "__main__":
    workspace = r"c:\Users\pathp\OneDrive\Desktop\Big Data Term Project"
    generate_all_charts(os.path.join(workspace, "data"), os.path.join(workspace, "figures"))
