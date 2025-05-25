import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_excel(file_path):
    """Load the Excel file and return the DataFrame."""
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns.")
        return df
    except Exception as e:
        logger.error(f"Error loading Excel file: {e}")
        raise

def handle_missing_values(df):
    """Replace missing or empty values with 'N/A' for appropriate columns."""
    # Columns to replace missing values with 'N/A'
    columns_to_clean = [
        'exit_load', 'rating', 'average_maturity', 'yield_to_maturity'
    ]
    
    for col in columns_to_clean:
        df[col] = df[col].replace([np.nan, '', None], 'N/A')
        logger.info(f"Replaced missing values in {col} with 'N/A'.")
    
    # For equity funds, ensure average_maturity and yield_to_maturity are 'N/A'
    df.loc[df['type'] == 'Equity', ['average_maturity', 'yield_to_maturity']] = 'N/A'
    
    return df

def standardize_data_types(df):
    """Ensure consistent data types for all columns."""
    # Numeric columns (float)
    numeric_cols = [
        'aum', 'nav', 'minimum_investment', 'minimum_sip_investment', 'pe', 'pb', 'debt_per', 'equity_per',
        'one_year_return', 'three_year_return', 'five_year_return', 'equity_aum'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna('N/A')
        logger.info(f"Converted {col} to numeric (float).")
    
    # String columns
    string_cols = ['name', 'risk', 'type', 'link']
    for col in string_cols:
        df[col] = df[col].astype(str)
    
    # Exit load and rating (special handling)
    df['exit_load'] = pd.to_numeric(df['exit_load'], errors='coerce').fillna('N/A')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce', downcast='integer').fillna('N/A')
    
    return df

def validate_data(df):
    """Validate data for outliers and consistency."""
    # Check for negative AUM, NAV, minimum_investment, minimum_sip_investment, or equity_aum
    for col in ['aum', 'nav', 'minimum_investment', 'minimum_sip_investment', 'equity_aum']:
        if col in df and (df[col].apply(lambda x: isinstance(x, (int, float)) and x < 0)).any():
            logger.warning(f"Negative values found in {col}.")
    
    # Check equity_aum <= aum
    valid_rows = df[df['equity_aum'].apply(lambda x: isinstance(x, (int, float))) & 
                   df['aum'].apply(lambda x: isinstance(x, (int, float)))]
    if (valid_rows['equity_aum'] > valid_rows['aum']).any():
        logger.warning(f"Equity AUM exceeds total AUM for some funds.")
    
    # Check for unrealistic returns (>100% or <-100%)
    for col in ['one_year_return', 'three_year_return', 'five_year_return']:
        if col in df:
            invalid = df[col].apply(lambda x: isinstance(x, (int, float)) and (x > 100 or x < -100))
            if invalid.any():
                logger.warning(f"Unrealistic returns found in {col}: {df[invalid][['name', col]]}")
    
    # Check debt_per + equity_per ≈ 100%
    valid_rows = df[df['debt_per'].apply(lambda x: isinstance(x, (int, float))) & 
                   df['equity_per'].apply(lambda x: isinstance(x, (int, float)))]
    total_allocation = valid_rows['debt_per'] + valid_rows['equity_per']
    if (total_allocation < 95).any() or (total_allocation > 105).any():
        logger.warning(f"Inconsistent debt_per + equity_per found in some funds.")
    
    # Check for duplicate funds
    if df['name'].duplicated().any():
        logger.warning(f"Duplicate fund names found: {df[df['name'].duplicated()]['name'].tolist()}")
    
    return df

def process_historical_nav(df):
    """Convert historical_nav into a separate DataFrame for time-series analysis."""
    nav_records = []
    for _, row in df.iterrows():
        fund_name = row['name']
        try:
            # Parse historical_nav (list of dictionaries)
            nav_data = row['historical_nav']
            if isinstance(nav_data, str):
                nav_data = json.loads(nav_data.replace("'", "\""))
            for entry in nav_data:
                nav_records.append({
                    'fund_name': fund_name,
                    'date': pd.to_datetime(entry['date']),
                    'nav': float(entry['nav'])
                })
        except Exception as e:
            logger.warning(f"Error processing historical_nav for {fund_name}: {e}")
    
    nav_df = pd.DataFrame(nav_records)
    
    # Validate NAVs
    if (nav_df['nav'] <= 0).any():
        logger.warning(f"Invalid NAV values (non-positive) found in historical_nav.")
    
    # Sort by fund and date
    nav_df = nav_df.sort_values(['fund_name', 'date']).reset_index(drop=True)
    logger.info(f"Created historical_nav DataFrame with {len(nav_df)} rows.")
    
    return nav_df

def process_top_holdings(df):
    """Convert top_holdings into a separate DataFrame for portfolio analysis."""
    holdings_records = []
    for _, row in df.iterrows():
        fund_name = row['name']
        try:
            # Parse top_holdings (list of dictionaries)
            holdings_data = row['top_holdings']
            if isinstance(holdings_data, str):
                holdings_data = json.loads(holdings_data.replace("'", "\""))
            for entry in holdings_data:
                holdings_records.append({
                    'fund_name': fund_name,
                    'company': entry['company'],
                    'percentage': float(entry['percentage'])
                })
        except Exception as e:
            logger.warning(f"Error processing top_holdings for {fund_name}: {e}")
    
    holdings_df = pd.DataFrame(holdings_records)
    
    # Validate percentages
    if (holdings_df['percentage'] <= 0).any():
        logger.warning(f"Invalid percentage values (non-positive) found in top_holdings.")
    
    # Check total percentage per fund
    total_per_fund = holdings_df.groupby('fund_name')['percentage'].sum()
    for fund, total in total_per_fund.items():
        if total < 20:
            logger.warning(f"Low total holdings percentage for {fund}: {total}%")
    
    logger.info(f"Created top_holdings DataFrame with {len(holdings_df)} rows.")
    
    return holdings_df

def process_asset_allocation(df):
    """Extract asset_allocation into separate columns and validate."""
    # Initialize new columns
    df['asset_equity'] = np.nan
    df['asset_debt'] = np.nan
    df['asset_cash'] = np.nan
    
    for idx, row in df.iterrows():
        fund_name = row['name']
        try:
            # Parse asset_allocation (dictionary)
            alloc_data = row['asset_allocation']
            if isinstance(alloc_data, str):
                alloc_data = json.loads(alloc_data.replace("'", "\""))
            
            df.at[idx, 'asset_equity'] = float(alloc_data.get('equity', np.nan))
            df.at[idx, 'asset_debt'] = float(alloc_data.get('debt', np.nan))
            df.at[idx, 'asset_cash'] = float(alloc_data.get('cash', np.nan))
            
            # Validate sum of allocations
            total = sum([alloc_data.get(key, 0) for key in ['equity', 'debt', 'cash'] if isinstance(alloc_data.get(key), (int, float))])
            if total < 95 or total > 105:
                logger.warning(f"Inconsistent asset allocation for {fund_name}: Total = {total}%")
        except Exception as e:
            logger.warning(f"Error processing asset_allocation for {fund_name}: {e}")
    
    # Convert to numeric and handle missing values
    for col in ['asset_equity', 'asset_debt', 'asset_cash']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna('N/A')
    
    logger.info("Processed asset_allocation into separate columns.")
    return df

def process_sector_allocation(df):
    """Convert sector_allocation into a separate DataFrame for analysis."""
    sector_records = []
    for _, row in df.iterrows():
        fund_name = row['name']
        try:
            # Parse sector_allocation (list of dictionaries)
            sector_data = row['sector_allocation']
            if isinstance(sector_data, str):
                sector_data = json.loads(sector_data.replace("'", "\""))
            for entry in sector_data:
                sector_records.append({
                    'fund_name': fund_name,
                    'sector': entry['sector'],
                    'percentage': float(entry['percentage'])
                })
        except Exception as e:
            logger.warning(f"Error processing sector_allocation for {fund_name}: {e}")
    
    sector_df = pd.DataFrame(sector_records)
    
    # Validate percentages
    if (sector_df['percentage'] <= 0).any():
        logger.warning(f"Invalid percentage values (non-positive) found in sector_allocation.")
    
    # Check total percentage per fund
    total_per_fund = sector_df.groupby('fund_name')['percentage'].sum()
    for fund, total in total_per_fund.items():
        if total < 90 or total > 110:
            logger.warning(f"Inconsistent sector allocation total for {fund}: {total}%")
    
    logger.info(f"Created sector_allocation DataFrame with {len(sector_df)} rows.")
    
    return sector_df

def simplify_complex_columns(df):
    """Simplify historical_nav, top_holdings, asset_allocation, and sector_allocation in the main DataFrame."""
    # Convert historical_nav to a string summary (e.g., latest NAV and date)
    def summarize_nav(nav_data):
        try:
            if isinstance(nav_data, str):
                nav_data = json.loads(nav_data.replace("'", "\""))
            latest = max(nav_data, key=lambda x: x['date'])
            return f"Latest NAV: {latest['nav']} on {latest['date']}"
        except:
            return "N/A"
    
    # Convert top_holdings to a string summary
    def summarize_holdings(holdings_data):
        try:
            if isinstance(holdings_data, str):
                holdings_data = json.loads(holdings_data.replace("'", "\""))
            return "; ".join([f"{h['company']} ({h['percentage']}%)" for h in holdings_data])
        except:
            return "N/A"
    
    # Convert asset_allocation to a string summary
    def summarize_asset_allocation(alloc_data):
        try:
            if isinstance(alloc_data, str):
                alloc_data = json.loads(alloc_data.replace("'", "\""))
            return f"Equity: {alloc_data.get('equity', 'N/A')}%, Debt: {alloc_data.get('debt', 'N/A')}%, Cash: {alloc_data.get('cash', 'N/A')}%"
        except:
            return "N/A"
    
    # Convert sector_allocation to a string summary
    def summarize_sector_allocation(sector_data):
        try:
            if isinstance(sector_data, str):
                sector_data = json.loads(sector_data.replace("'", "\""))
            return "; ".join([f"{s['sector']} ({s['percentage']}%)" for s in sector_data])
        except:
            return "N/A"
    
    df['historical_nav_summary'] = df['historical_nav'].apply(summarize_nav)
    df['top_holdings_summary'] = df['top_holdings'].apply(summarize_holdings)
    df['asset_allocation_summary'] = df['asset_allocation'].apply(summarize_asset_allocation)
    df['sector_allocation_summary'] = df['sector_allocation'].apply(summarize_sector_allocation)
    
    # Drop original complex columns
    df = df.drop(['historical_nav', 'top_holdings', 'asset_allocation', 'sector_allocation'], axis=1)
    
    return df

def save_cleaned_data(fund_df, nav_df, holdings_df, sector_df, output_file):
    """Save the cleaned data to an Excel file with multiple sheets."""
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            fund_df.to_excel(writer, sheet_name='Fund_Data', index=False)
            nav_df.to_excel(writer, sheet_name='Historical_NAV', index=False)
            holdings_df.to_excel(writer, sheet_name='Top_Holdings', index=False)
            sector_df.to_excel(writer, sheet_name='Sector_Allocation', index=False)
        logger.info(f"Saved cleaned data to {output_file}.")
    except Exception as e:
        logger.error(f"Error saving Excel file: {e}")
        raise

def preprocess_data(input_file, output_file):
    """Main function to preprocess the Excel file."""
    # Load data
    df = load_excel(input_file)
    
    # Handle missing values
    df = handle_missing_values(df)
    
    # Standardize data types
    df = standardize_data_types(df)
    
    # Validate data
    df = validate_data(df)
    
    # Process historical_nav
    nav_df = process_historical_nav(df)
    
    # Process top_holdings
    holdings_df = process_top_holdings(df)
    
    # Process asset_allocation
    df = process_asset_allocation(df)
    
    # Process sector_allocation
    sector_df = process_sector_allocation(df)
    
    # Simplify complex columns in main DataFrame
    df = simplify_complex_columns(df)
    
    # Save cleaned data
    save_cleaned_data(df, nav_df, holdings_df, sector_df, output_file)
    
    return df, nav_df, holdings_df, sector_df

if __name__ == "__main__":
    input_file = "raw_data.xlsx"
    output_file = "cleaned_data.xlsx"
    fund_df, nav_df, holdings_df, sector_df = preprocess_data(input_file, output_file)
    
    # Display sample data
    print("Fund Data Sample:")
    print(fund_df.head())
    print("\nHistorical NAV Sample:")
    print(nav_df.head())
    print("\nTop Holdings Sample:")
    print(holdings_df.head())
    print("\nSector Allocation Sample:")
    print(sector_df.head())