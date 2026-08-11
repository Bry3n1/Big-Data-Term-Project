import os
import numpy as np
import pandas as pd

def run_rfm_segmentation(df_customers, df_orders, df_order_items):
    """
    Performs customer RFM segmentation using raw NumPy arrays.
    R: Recency (days since last purchase relative to max date)
    F: Frequency (number of unique orders)
    M: Monetary (total net spend)
    """
    # 1. Merge and filter for completed/returned
    df_sales = pd.merge(df_order_items, df_orders, on='order_id')
    df_sales = df_sales[df_sales['status'].isin(['completed', 'returned'])]
    df_sales['net_revenue'] = df_sales['quantity'] * df_sales['unit_price'] * (1 - df_sales['discount'])
    
    # Max date in dataset
    max_date = df_sales['order_date'].max()
    
    # Aggregate by customer
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
    max_date = pd.to_datetime(max_date)
    
    cust_rfm = df_sales.groupby('customer_id').agg({
        'order_date': lambda x: (max_date - x.max()).days, # Recency
        'order_id': 'nunique',                             # Frequency
        'net_revenue': 'sum'                               # Monetary
    }).rename(columns={
        'order_date': 'recency',
        'order_id': 'frequency',
        'net_revenue': 'monetary'
    })
    
    # Include customers with 0 purchases
    all_cust_ids = df_customers['customer_id'].unique()
    cust_rfm = cust_rfm.reindex(all_cust_ids, fill_value=0)
    # For recency, 0-purchase customers should have maximum recency (e.g. max age of database history)
    # Let's check max recency of active customers and add 365 days
    max_active_recency = cust_rfm['recency'].max()
    cust_rfm.loc[cust_rfm['recency'] == 0, 'recency'] = max_active_recency + 365
    
    # 2. Convert to NumPy arrays
    r_arr = cust_rfm['recency'].to_numpy()
    f_arr = cust_rfm['frequency'].to_numpy()
    m_arr = cust_rfm['monetary'].to_numpy()
    
    # 3. Calculate quintile cutoffs manually using np.percentile
    # Recency: lower is better (gets score 5)
    r_pcts = np.percentile(r_arr[r_arr < max_active_recency + 300], [20, 40, 60, 80]) # Exclude non-purchasers for quintile calculation
    # Frequency: higher is better (gets score 5)
    f_pcts = np.percentile(f_arr[f_arr > 0], [20, 40, 60, 80])
    # Monetary: higher is better (gets score 5)
    m_pcts = np.percentile(m_arr[m_arr > 0], [20, 40, 60, 80])
    
    # Assign scores using digitize
    # Recency: 1 is worst, 5 is best (reversed bins)
    r_scores = 5 - np.digitize(r_arr, r_pcts) + 1
    # Handle non-purchasers (explicitly set to 1)
    r_scores[r_arr >= max_active_recency + 300] = 1
    
    f_scores = np.digitize(f_arr, f_pcts) + 1
    f_scores[f_arr == 0] = 1
    
    m_scores = np.digitize(m_arr, m_pcts) + 1
    m_scores[m_arr <= 0] = 1
    
    # Combine scores
    rfm_score = r_scores + f_scores + m_scores
    
    # Add back to DataFrame
    cust_rfm['R_score'] = r_scores
    cust_rfm['F_score'] = f_scores
    cust_rfm['M_score'] = m_scores
    cust_rfm['rfm_score'] = rfm_score
    
    # Segment definition
    # Champions: score >= 12
    # Loyal Customers: score 9-11
    # Potential Loyalists: score 7-8
    # At Risk: score 5-6
    # Lost Customers: score 3-4
    def get_segment(score):
        if score >= 12:
            return 'Champions'
        elif score >= 9:
            return 'Loyal Customers'
        elif score >= 7:
            return 'Potential Loyalists'
        elif score >= 5:
            return 'At Risk'
        else:
            return 'Lost Customers'
            
    cust_rfm['rfm_segment'] = cust_rfm['rfm_score'].apply(get_segment)
    
    return cust_rfm, {
        'r_pcts': r_pcts,
        'f_pcts': f_pcts,
        'm_pcts': m_pcts
    }

def run_product_recommendations(df_customers, df_products, df_orders, df_order_items, sample_cust_ids):
    """
    Builds a product-product similarity matrix and generates recommendations.
    Uses manual cosine similarity in NumPy.
    """
    # 1. Build customer-product purchase quantity matrix
    df_sales = pd.merge(df_order_items, df_orders, on='order_id')
    df_sales = df_sales[df_sales['status'].isin(['completed', 'returned'])]
    
    # Group by customer and product to find total quantity bought (returns are filtered or included? Keep positive buys for recommendation)
    df_sales_pos = df_sales[df_sales['quantity'] > 0]
    
    cust_prod_pivot = df_sales_pos.pivot_table(
        index='customer_id',
        columns='product_id',
        values='quantity',
        aggfunc='sum'
    ).fillna(0)
    
    # Align with all customer ids and product ids
    all_cust_ids = df_customers['customer_id'].unique()
    all_prod_ids = df_products['product_id'].unique()
    
    cust_prod_pivot = cust_prod_pivot.reindex(index=all_cust_ids, columns=all_prod_ids, fill_value=0)
    
    # Convert to NumPy array R of shape (C, P)
    R = cust_prod_pivot.to_numpy()
    
    # 2. Compute product similarity matrix S of shape (P, P) using NumPy
    # S_ij = dot(P_i, P_j) / (norm(P_i) * norm(P_j))
    # We can do this by normalizing columns of R first
    col_norms = np.linalg.norm(R, axis=0)
    # Avoid division by zero
    col_norms_clean = np.where(col_norms == 0, 1e-9, col_norms)
    
    R_normalized = R / col_norms_clean
    
    # S = R_normalized^T * R_normalized
    S = np.dot(R_normalized.T, R_normalized)
    
    # Ensure diagonal is 1
    np.fill_diagonal(S, 1.0)
    
    # 3. Generate recommendations for sample customers
    recommendations = {}
    
    for cust_id in sample_cust_ids:
        # Get customer row index
        cust_idx = cust_prod_pivot.index.get_loc(cust_id)
        cust_vector = R[cust_idx]
        
        # Calculate predicted interest scores for all products
        # predicted_scores = cust_vector * S
        predicted_scores = np.dot(cust_vector, S)
        
        # Mask products already purchased
        already_purchased = cust_vector > 0
        predicted_scores[already_purchased] = -1.0 # Set below zero
        
        # Get top 3 product indices
        top_indices = np.argsort(predicted_scores)[::-1][:3]
        top_product_ids = cust_prod_pivot.columns[top_indices].tolist()
        
        recommendations[cust_id] = {
            'purchased': cust_prod_pivot.columns[already_purchased].tolist()[:10], # Sample of what they bought
            'recommended': top_product_ids
        }
        
    return S, recommendations, cust_prod_pivot.columns.tolist()

def run_linear_regression(df_orders, df_order_items):
    """
    Fits Monthly Revenue = f(Month Index) using the Normal Equation.
    beta = (X^T * X)^-1 * X^T * y
    """
    # 1. Prepare data: Monthly revenue
    df_sales = pd.merge(df_order_items, df_orders, on='order_id')
    df_sales = df_sales[df_sales['status'].isin(['completed', 'returned'])]
    df_sales['net_revenue'] = df_sales['quantity'] * df_sales['unit_price'] * (1 - df_sales['discount'])
    
    df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])
    df_monthly = df_sales.groupby(df_sales['order_date'].dt.to_period('M'))['net_revenue'].sum().reset_index()
    
    # Filter for the last 24 months of data (e.g. 2023-01 to 2024-12)
    df_monthly = df_monthly.sort_values(by='order_date')
    df_monthly = df_monthly.tail(24).reset_index(drop=True)
    
    # Month index 1 to 24
    month_indices = np.arange(1, 25)
    revenues = df_monthly['net_revenue'].to_numpy()
    
    # 2. X and y matrices
    y = revenues
    # X has ones for intercept, and month indices for slope
    X = np.column_stack((np.ones_like(month_indices), month_indices))
    
    # 3. Fit via normal equation
    # beta = inv(X^T * X) * X^T * y
    X_T_X = np.dot(X.T, X)
    X_T_y = np.dot(X.T, y)
    beta = np.dot(np.linalg.inv(X_T_X), X_T_y)
    
    # 4. Predictions & R^2
    y_pred = np.dot(X, beta)
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean) ** 2)
    ss_res = np.sum((y - y_pred) ** 2)
    r2 = 1.0 - (ss_res / ss_tot)
    
    # Standard error of predictions
    mse = ss_res / (len(y) - 2)
    std_err = np.sqrt(mse)
    
    return beta, r2, y, y_pred, std_err, df_monthly['order_date'].dt.strftime('%Y-%m').tolist()

def run_monte_carlo_simulation(df_order_items, df_orders, df_products, num_trials=5000):
    """
    Simulates stockout probability over a 30-day lead time for the top 3 revenue generating products.
    """
    # 1. Identify top 3 revenue products
    df_sales = pd.merge(df_order_items, df_orders, on='order_id')
    df_sales = df_sales[df_sales['status'].isin(['completed', 'returned'])]
    df_sales['net_revenue'] = df_sales['quantity'] * df_sales['unit_price'] * (1 - df_sales['discount'])
    
    top_prods = df_sales.groupby('product_id')['net_revenue'].sum().sort_values(ascending=False).head(3).index.tolist()
    
    # 2. Extract daily demand profiles for these products
    df_sales['order_date_only'] = pd.to_datetime(df_sales['order_date']).dt.date
    
    # We only count positive quantity demands (representing purchases) for stockout simulations
    df_purchases = df_sales[df_sales['quantity'] > 0]
    
    sim_results = {}
    
    for prod_id in top_prods:
        prod_name = df_products[df_products['product_id'] == prod_id]['name'].values[0]
        prod_stock = df_products[df_products['product_id'] == prod_id]['in_stock_units'].values[0]
        
        # Daily sales volumes
        daily_sales = df_purchases[df_purchases['product_id'] == prod_id].groupby('order_date_only')['quantity'].sum()
        
        # Fill missing dates with 0 (since no sales means 0 demand)
        all_dates = pd.date_range(start=df_purchases['order_date_only'].min(), end=df_purchases['order_date_only'].max())
        daily_sales = daily_sales.reindex(all_dates.date, fill_value=0)
        
        sales_arr = daily_sales.to_numpy()
        mean_demand = np.mean(sales_arr)
        std_demand = np.std(sales_arr)
        
        # Simulate 30 days demand for 5,000 trials
        np.random.seed(42) # Set seed for reproducibility
        daily_sims = np.random.normal(loc=mean_demand, scale=std_demand, size=(num_trials, 30))
        daily_sims = np.clip(daily_sims, 0, None) # Clamp daily demand to >= 0
        simulated_demands = np.sum(daily_sims, axis=1)
        
        # Count stockouts (where simulated demand > in_stock_units)
        stockouts = simulated_demands > prod_stock
        stockout_prob = np.mean(stockouts)
        
        # 95% Confidence Interval for stockout probability
        ci_err = 1.96 * np.sqrt((stockout_prob * (1 - stockout_prob)) / num_trials)
        ci = (max(0.0, stockout_prob - ci_err), min(1.0, stockout_prob + ci_err))
        
        # Reorder point: 95th percentile of demand (which guarantees 5% stockout risk)
        reorder_point = np.percentile(simulated_demands, 95)
        
        sim_results[prod_id] = {
            'product_name': prod_name,
            'initial_stock': prod_stock,
            'mean_daily_demand': mean_demand,
            'std_daily_demand': std_demand,
            'simulated_demands': simulated_demands,
            'stockout_probability': stockout_prob,
            'confidence_interval': ci,
            'reorder_point': reorder_point
        }
        
    return sim_results

def run_numpy_analysis_pipeline(processed_dir):
    """Loads processed files and runs Phase 3 NumPy analytical methods."""
    df_customers = pd.read_csv(os.path.join(processed_dir, "clean_customers.csv"))
    df_products = pd.read_csv(os.path.join(processed_dir, "clean_products.csv"))
    df_orders = pd.read_csv(os.path.join(processed_dir, "clean_orders.csv"))
    df_order_items = pd.read_csv(os.path.join(processed_dir, "clean_order_items.csv"))
    
    # 1. RFM Segmentation
    df_rfm, rfm_pcts = run_rfm_segmentation(df_customers, df_orders, df_order_items)
    df_rfm.to_csv(os.path.join(processed_dir, "customer_rfm_scores.csv"))
    
    # 2. Recommendations
    sample_custs = [10, 20, 30, 40, 50]
    S, recs, prod_ids = run_product_recommendations(df_customers, df_products, df_orders, df_order_items, sample_custs)
    
    # Save recommendations to file
    rec_rows = []
    for cid, data in recs.items():
        rec_rows.append({
            'customer_id': cid,
            'purchased': ", ".join(map(str, data['purchased'])),
            'recommended': ", ".join(map(str, data['recommended']))
        })
    df_recs = pd.DataFrame(rec_rows)
    df_recs.to_csv(os.path.join(processed_dir, "sample_recommendations.csv"), index=False)
    
    # Save cosine similarity matrix
    np.save(os.path.join(processed_dir, "product_similarity_matrix.npy"), S)
    
    # 3. Linear Regression
    beta, r2, y, y_pred, std_err, months = run_linear_regression(df_orders, df_order_items)
    
    # Save regression coefficients
    df_reg = pd.DataFrame({
        'parameter': ['intercept (beta_0)', 'slope (beta_1)'],
        'coefficient': beta
    })
    df_reg.to_csv(os.path.join(processed_dir, "regression_coefficients.csv"), index=False)
    
    # 4. Monte Carlo Stockout Simulation
    sim_results = run_monte_carlo_simulation(df_order_items, df_orders, df_products)
    
    # Save MC stats to file
    mc_rows = []
    for pid, data in sim_results.items():
        mc_rows.append({
            'product_id': pid,
            'product_name': data['product_name'],
            'initial_stock': data['initial_stock'],
            'mean_daily_demand': data['mean_daily_demand'],
            'std_daily_demand': data['std_daily_demand'],
            'stockout_probability': data['stockout_probability'],
            'ci_lower': data['confidence_interval'][0],
            'ci_upper': data['confidence_interval'][1],
            'reorder_point': data['reorder_point']
        })
    df_mc = pd.DataFrame(mc_rows)
    df_mc.to_csv(os.path.join(processed_dir, "monte_carlo_stockout_stats.csv"), index=False)
    
    print("--- Phase 3 NumPy Analytical Methods Finished ---")
    print(f"RFM customer scores generated: {len(df_rfm)}")
    print(f"Recommendations generated for sample customer IDs: {sample_custs}")
    print(f"Regression completed: intercept={beta[0]:.2f}, slope={beta[1]:.2f}, R2={r2:.4f}")
    for pid, data in sim_results.items():
        print(f"Product {pid} MC Simulation: stockout_prob={data['stockout_probability']*100:.1f}%, reorder_point={data['reorder_point']:.1f}")
        
    return {
        'rfm_segments': df_rfm['rfm_segment'].value_counts().to_dict(),
        'recs': recs,
        'regression': {'beta': beta.tolist(), 'r2': r2, 'std_err': std_err},
        'mc': sim_results
    }

if __name__ == "__main__":
    workspace = r"c:\Users\pathp\OneDrive\Desktop\Big Data Term Project"
    run_numpy_analysis_pipeline(os.path.join(workspace, "data", "processed"))
