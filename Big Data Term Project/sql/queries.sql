-- ==============================================================================
-- UrbanCart Big Data Project — Phase 1: SQL Data Extraction
-- ==============================================================================

-- Query 1: What is the total revenue, total orders count, and average order value (AOV) for each product category (net of discounts and returns)?
SELECT 
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS total_revenue,
    COUNT(DISTINCT oi.order_id) AS order_count,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) / COUNT(DISTINCT oi.order_id), 2) AS average_order_value
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status IN ('completed', 'returned')
GROUP BY p.category
ORDER BY total_revenue DESC;

-- Query 2: Who are the top 20 customers by lifetime spend (excluding cancelled/pending orders), and where/when did they sign up?
SELECT 
    c.customer_id,
    c.name,
    c.email,
    c.city,
    c.signup_date,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS lifetime_spend
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status IN ('completed', 'returned')
GROUP BY c.customer_id, c.name, c.email, c.city, c.signup_date
ORDER BY lifetime_spend DESC
LIMIT 20;

-- Query 3: What is the month-over-month (MoM) revenue trend and running revenue total for the last 24 months of sales data?
WITH MonthlyRevenue AS (
    SELECT 
        STRFTIME('%Y-%m', o.order_date) AS order_month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status IN ('completed', 'returned')
      AND o.order_date >= '2023-01-01'
    GROUP BY order_month
)
SELECT 
    order_month,
    ROUND(monthly_revenue, 2) AS monthly_revenue,
    ROUND(LAG(monthly_revenue) OVER (ORDER BY order_month), 2) AS prev_month_revenue,
    ROUND(monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY order_month), 2) AS mom_revenue_change,
    ROUND(SUM(monthly_revenue) OVER (ORDER BY order_month), 2) AS running_total_revenue
FROM MonthlyRevenue
ORDER BY order_month;

-- Query 4: What is the customer return rate (measured as the ratio of returned order items to total order items) across product categories?
WITH CategoryItems AS (
    SELECT 
        p.category,
        COUNT(*) AS total_items,
        SUM(CASE WHEN oi.quantity < 0 THEN 1 ELSE 0 END) AS return_items
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status IN ('completed', 'returned')
    GROUP BY p.category
)
SELECT 
    category,
    total_items,
    return_items,
    ROUND(return_items * 100.0 / total_items, 2) AS return_rate_percent
FROM CategoryItems
ORDER BY return_rate_percent DESC;

-- Query 5: Which customers have demonstrated consistent ordering behavior by placing at least one order in every one of the last three quarters of 2024?
SELECT 
    c.customer_id,
    c.name,
    c.email,
    COUNT(DISTINCT (STRFTIME('%Y', o.order_date) || '-Q' || ((CAST(STRFTIME('%m', o.order_date) AS INTEGER) - 1) / 3 + 1))) AS quarters_active
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-04-01' AND o.order_date <= '2024-12-31'
GROUP BY c.customer_id, c.name, c.email
HAVING quarters_active = 3;

-- Query 6: Which top 10 products have the highest average customer review rating among those with a statistically significant sample size of at least 15 reviews?
SELECT 
    p.product_id,
    p.name AS product_name,
    p.category,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    COUNT(r.review_id) AS review_count
FROM products p
JOIN reviews r ON p.product_id = r.product_id
WHERE r.rating BETWEEN 1 AND 5
GROUP BY p.product_id, p.name, p.category
HAVING review_count >= 15
ORDER BY avg_rating DESC, review_count DESC
LIMIT 10;

-- Query 7: What are the average session duration and average number of pages viewed by customers across different device types, for customers who have made at least one purchase?
SELECT 
    ws.device,
    ROUND(AVG(ws.duration_minutes), 2) AS avg_session_duration_mins,
    ROUND(AVG(ws.pages_viewed), 2) AS avg_pages_viewed,
    COUNT(*) AS total_sessions
FROM web_sessions ws
WHERE EXISTS (
    SELECT 1 
    FROM orders o 
    WHERE o.customer_id = ws.customer_id
)
GROUP BY ws.device;

-- Query 8: How do products rank in terms of revenue generated within each individual product category?
WITH ProductRevenue AS (
    SELECT 
        p.category,
        p.product_id,
        p.name AS product_name,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS total_revenue
    FROM products p
    JOIN order_items oi ON p.product_id = oi.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status IN ('completed', 'returned')
    GROUP BY p.category, p.product_id, p.name
)
SELECT 
    category,
    product_id,
    product_name,
    total_revenue,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rev_rank
FROM ProductRevenue
ORDER BY category, rev_rank;

-- Query 9: What is the distribution and percentage share of different payment methods used by customers in each country?
WITH PaymentCounts AS (
    SELECT 
        c.country,
        o.payment_method,
        COUNT(o.order_id) AS method_order_count
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.country, o.payment_method
),
CountryTotals AS (
    SELECT 
        country,
        SUM(method_order_count) AS total_order_count
    FROM PaymentCounts
    GROUP BY country
)
SELECT 
    pc.country,
    pc.payment_method,
    pc.method_order_count,
    ct.total_order_count,
    ROUND(pc.method_order_count * 100.0 / ct.total_order_count, 2) AS payment_share_percent
FROM PaymentCounts pc
JOIN CountryTotals ct ON pc.country = ct.country
ORDER BY pc.country, payment_share_percent DESC;

-- Query 10: How do order volume, total net revenue, average order value, and return rates vary across different customer age groups, and what are the strategic implications?
WITH AgeGroups AS (
    SELECT 
        o.order_id,
        o.customer_id,
        CASE 
            WHEN c.age IS NULL THEN 'Unknown'
            WHEN c.age < 25 THEN 'Under 25'
            WHEN c.age BETWEEN 25 AND 40 THEN '25-40'
            WHEN c.age BETWEEN 41 AND 60 THEN '41-60'
            ELSE 'Over 60'
        END AS age_group
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
),
RevenueAndItems AS (
    SELECT 
        ag.age_group,
        COUNT(DISTINCT ag.order_id) AS total_orders,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS gross_revenue,
        SUM(CASE WHEN oi.quantity < 0 THEN 1 ELSE 0 END) AS total_returns,
        COUNT(*) AS total_items
    FROM order_items oi
    JOIN AgeGroups ag ON oi.order_id = ag.order_id
    GROUP BY ag.age_group
)
SELECT 
    age_group,
    total_orders,
    ROUND(gross_revenue, 2) AS net_revenue,
    ROUND(gross_revenue / total_orders, 2) AS avg_order_value,
    ROUND(total_returns * 100.0 / total_items, 2) AS return_rate_percent
FROM RevenueAndItems
ORDER BY net_revenue DESC;
