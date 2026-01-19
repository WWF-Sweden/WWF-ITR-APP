"""
Data loading utilities for WWF ITR Tool.
Handles Excel/CSV file loading and data validation.
"""
from asyncio.log import logger
import os
import tempfile
import urllib.request
import pandas as pd
import streamlit as st
from typing import Optional, Tuple

import ITR
from ITR.data.excel import ExcelProvider


@st.cache_data(show_spinner="Loading sample data...")
def download_sample_data(data_dir: str = "data") -> Tuple[str, str]:
    """
    Download sample data files from GitHub if not present locally.
    
    Args:
        data_dir: Directory to store downloaded files
        
    Returns:
        Tuple of (provider_path, portfolio_path)
    """
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)
    
    provider_path = os.path.join(data_dir, "data_provider_example.xlsx")
    portfolio_path = os.path.join(data_dir, "example_portfolio.csv")
    
    if not os.path.isfile(provider_path):
        urllib.request.urlretrieve(
            "https://github.com/WWF-Sweden/ITR-tool/raw/main/examples/data/data_provider_example.xlsx",
            provider_path
        )
    
    if not os.path.isfile(portfolio_path):
        urllib.request.urlretrieve(
            "https://github.com/WWF-Sweden/ITR-tool/raw/main/examples/data/example_portfolio.csv",
            portfolio_path
        )
    
    return provider_path, portfolio_path


@st.cache_resource(show_spinner="Loading provider data...")
def load_provider_data(file_path: str) -> ExcelProvider:
    """
    Load fundamental and target data from Excel file.
    
    Args:
        file_path: Path to the Excel file containing provider data
        
    Returns:
        ExcelProvider instance
    """
    return ExcelProvider(path=file_path)


@st.cache_data(show_spinner="Loading portfolio data...")
def load_portfolio_data(file_path: str) -> pd.DataFrame:
    """
    Load portfolio data from CSV file.
    
    Args:
        file_path: Path to the CSV file containing portfolio data
        
    Returns:
        DataFrame with portfolio data
    """
    return pd.read_csv(file_path, encoding="iso-8859-1")

def load_uploaded_provider_file(uploaded_file):
    """Save uploaded provider file to temporary location."""
    # Use system temp directory instead of uploads folder
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    return tmp_path


def load_uploaded_portfolio_file(uploaded_file):
    """Save uploaded portfolio file to temporary location and load as DataFrame."""
    # Use system temp directory
    suffix = '.csv' if uploaded_file.name.endswith('.csv') else '.xlsx'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    # Read the file into DataFrame
    try:
        if suffix == '.csv':
            df = pd.read_csv(tmp_path)
        else:
            df = pd.read_excel(tmp_path)
        return df
    except Exception as e:
        logger.error(f"Error reading uploaded portfolio file: {e}")
        raise
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def convert_portfolio_to_companies(portfolio_df: pd.DataFrame) -> list:
    """
    Convert portfolio DataFrame to list of PortfolioCompany objects.
    
    Args:
        portfolio_df: DataFrame with portfolio data
        
    Returns:
        List of PortfolioCompany objects
    """
    return ITR.utils.dataframe_to_portfolio(portfolio_df)


def validate_portfolio_data(portfolio_df: pd.DataFrame) -> Tuple[bool, list]:
    """
    Validate that portfolio data has required columns.
    
    Args:
        portfolio_df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, list of missing columns)
    """
    required_columns = ['company_id', 'investment_value']
    missing = [col for col in required_columns if col not in portfolio_df.columns]
    return len(missing) == 0, missing


def validate_provider_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate that provider file can be loaded.
    
    Args:
        file_path: Path to Excel file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ExcelProvider(path=file_path)
        return True, ""
    except Exception as e:
        return False, str(e)
