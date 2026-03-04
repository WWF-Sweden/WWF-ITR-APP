"""
Data source selection for WWF ITR Tool.
Allows users to choose between example data or proprietary uploads.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional


def select_data_source() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    Prompt user to select data source: example files or upload.
    
    Returns:
        Tuple of (portfolio_df, fundamentals_df, source_type)
    """
    st.subheader("📊 Data Source Selection")
    
    data_option = st.radio(
        "Choose your data source:",
        options=["Use Example Data", "Upload Proprietary Data"],
        horizontal=True,
        help="Example data is provided for demonstration. Upload your own files for actual analysis."
    )
    
    portfolio_df = None
    fundamentals_df = None
    
    if data_option == "Use Example Data":
        st.info("📁 Using built-in example data files for demonstration.")
        portfolio_df, fundamentals_df = load_example_data()
        source_type = "example"
        
    else:  # Upload Proprietary Data
        st.warning("⚠️ Please upload your portfolio and company fundamentals files.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            portfolio_file = st.file_uploader(
                "Upload Portfolio CSV/Excel",
                type=["csv", "xlsx"],
                key="portfolio_upload",
                help="File should contain: company_id, company_name, investment_value, etc."
            )
            
        with col2:
            fundamentals_file = st.file_uploader(
                "Upload Company Fundamentals CSV/Excel",
                type=["csv", "xlsx"],
                key="fundamentals_upload",
                help="File should contain: company_id, sector, region, emissions data, etc."
            )
        
        if portfolio_file and fundamentals_file:
            portfolio_df = read_uploaded_file(portfolio_file)
            fundamentals_df = read_uploaded_file(fundamentals_file)
            source_type = "uploaded"
        else:
            source_type = "incomplete"
    
    return portfolio_df, fundamentals_df, source_type


def load_example_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load example data files from the data directory."""
    data_dir = Path(__file__).parent.parent / "data" / "examples"
    
    # Adjust paths to your actual example file locations
    portfolio_path = data_dir / "example_portfolio.csv"
    fundamentals_path = data_dir / "example_fundamentals.csv"
    
    try:
        portfolio_df = pd.read_csv(portfolio_path)
        fundamentals_df = pd.read_csv(fundamentals_path)
        st.success(f"✅ Loaded example data: {len(portfolio_df)} portfolio entries, {len(fundamentals_df)} companies")
        return portfolio_df, fundamentals_df
    except FileNotFoundError as e:
        st.error(f"Example data files not found: {e}")
        return None, None


def read_uploaded_file(uploaded_file) -> Optional[pd.DataFrame]:
    """Read uploaded CSV or Excel file."""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.success(f"✅ Loaded {uploaded_file.name}: {len(df)} rows")
        return df
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}")
        return None


def validate_data(portfolio_df: pd.DataFrame, fundamentals_df: pd.DataFrame) -> bool:
    """
    Validate that uploaded data has required columns.
    
    Args:
        portfolio_df: Portfolio data
        fundamentals_df: Company fundamentals data
        
    Returns:
        True if valid, False otherwise
    """
    required_portfolio_cols = ['company_id', 'investment_value']
    required_fundamentals_cols = ['company_id']
    
    missing_portfolio = [c for c in required_portfolio_cols if c not in portfolio_df.columns]
    missing_fundamentals = [c for c in required_fundamentals_cols if c not in fundamentals_df.columns]
    
    is_valid = True
    
    if missing_portfolio:
        st.error(f"❌ Portfolio file missing required columns: {missing_portfolio}")
        st.info(f"Available columns: {list(portfolio_df.columns)}")
        is_valid = False
        
    if missing_fundamentals:
        st.error(f"❌ Fundamentals file missing required columns: {missing_fundamentals}")
        st.info(f"Available columns: {list(fundamentals_df.columns)}")
        is_valid = False
    
    if is_valid:
        # Check for matching company_ids
        portfolio_ids = set(portfolio_df['company_id'].unique())
        fundamentals_ids = set(fundamentals_df['company_id'].unique())
        matched = portfolio_ids.intersection(fundamentals_ids)
        
        if len(matched) == 0:
            st.error("❌ No matching company_id values between portfolio and fundamentals files")
            is_valid = False
        else:
            match_pct = (len(matched) / len(portfolio_ids)) * 100
            st.info(f"ℹ️ {len(matched)} of {len(portfolio_ids)} portfolio companies ({match_pct:.1f}%) found in fundamentals data")
    
    return is_valid


def data_preview(portfolio_df: pd.DataFrame, fundamentals_df: pd.DataFrame) -> None:
    """Show a preview of the loaded data."""
    with st.expander("📋 Preview Loaded Data", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Portfolio Data**")
            st.dataframe(portfolio_df.head(10), width="stretch")
            
        with col2:
            st.write("**Fundamentals Data**")
            st.dataframe(fundamentals_df.head(10), width="stretch")