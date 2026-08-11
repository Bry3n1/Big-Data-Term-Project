import os
import sys
from data_loading import load_all_raw_data
from cleaning import run_cleaning_pipeline
from numpy_analysis import run_numpy_analysis_pipeline
from visualizations import generate_all_charts

def run_full_pipeline(workspace_dir):
    """Runs the end-to-end data pipeline from raw files to final figures."""
    print("======================================================================")
    print("   Starting UrbanCart Retail Intelligence Analytics Pipeline          ")
    print("======================================================================")
    
    data_dir = os.path.join(workspace_dir, "data")
    fig_dir = os.path.join(workspace_dir, "figures")
    processed_dir = os.path.join(data_dir, "processed")
    
    # Ensure directories exist
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    # Step 1: Loading & Cleaning (Phase 2)
    print("\n[Step 1/3] Running Data Loading & Cleaning Pipeline...")
    cleaning_stats = run_cleaning_pipeline(data_dir)
    print("[OK] Loading & Cleaning finished successfully.")
    print(f"   - Price Outliers Capped: {cleaning_stats['outliers_count']}")
    print(f"   - Duplicate Order Items Removed: {cleaning_stats['dedup_stats']['duplicates_removed']}")
    print(f"   - Out-of-Range Review Ratings Corrected: {cleaning_stats['invalid_ratings_count']}")
    
    # Step 2: NumPy Analytical Methods (Phase 3)
    print("\n[Step 2/3] Running NumPy Analytical Calculations...")
    analysis_stats = run_numpy_analysis_pipeline(processed_dir)
    print("[OK] NumPy Analytical Calculations finished successfully.")
    
    # Step 3: Visualization Generation (Phase 4)
    print("\n[Step 3/3] Generating Business Charts & Visualizations...")
    generate_all_charts(data_dir, fig_dir)
    print("[OK] All charts generated and saved in figures/ folder.")
    
    print("\n======================================================================")
    print("   Pipeline Completed Successfully! All outputs are saved and verified.")
    print("======================================================================")

if __name__ == "__main__":
    # Get workspace directory
    workspace = r"c:\Users\pathp\OneDrive\Desktop\Big Data Term Project"
    run_full_pipeline(workspace)
