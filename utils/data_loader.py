"""
Data loading utilities for WWF ITR Tool.
Handles Excel/CSV file loading, data validation, and database persistence.
"""
from asyncio.log import logger
import os
import tempfile
import urllib.request
import pandas as pd
import streamlit as st
from typing import Dict, Optional, Tuple

import ITR
from ITR.data.excel import ExcelProvider

from db.database import (
    init_db,
    save_dataset,
    load_dataset,
    list_datasets,
    delete_dataset,
    update_table,
)


_PORTFOLIO_REQUIRED_COLS = ["company_id", "company_name", "investment_value"]


def _drop_empty_rows(df: pd.DataFrame, key_col: str = "company_id") -> pd.DataFrame:
    """Drop rows missing key_col (NaN or empty string). Used for fundamentals/targets."""
    if key_col not in df.columns:
        return df
    mask = df[key_col].isna() | (df[key_col].astype(str).str.strip() == "")
    return df[~mask].reset_index(drop=True)


def clean_portfolio_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Drop portfolio rows that are missing or have invalid required fields.

    Returns:
        Tuple of (cleaned DataFrame, number of rows dropped).
    """
    if df.empty:
        return df, 0
    invalid = pd.Series(False, index=df.index)
    # String columns: must not be NaN or blank
    for col in ("company_id", "company_name"):
        if col in df.columns:
            invalid |= df[col].isna() | (df[col].astype(str).str.strip() == "")
    # Numeric column: must be a positive number
    if "investment_value" in df.columns:
        numeric_vals = pd.to_numeric(df["investment_value"], errors="coerce")
        invalid |= numeric_vals.isna() | (numeric_vals <= 0)
    cleaned = df[~invalid].reset_index(drop=True)
    return cleaned, int(invalid.sum())


def clean_fundamental_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Validate and clean a fundamentals DataFrame.

    - Drops rows missing company_id or company_name (the row identifiers).
    - Fills NaN in isic and other string fields with '' (matching ExcelProvider behaviour).
    - Coerces numeric columns to float so Pydantic won't reject junk text.

    Returns:
        Tuple of (cleaned DataFrame, number of rows dropped).
    """
    if df.empty:
        return df, 0
    invalid = pd.Series(False, index=df.index)
    # Only drop rows missing the two key identifiers
    for col in ("company_id", "company_name"):
        if col in df.columns:
            invalid |= df[col].isna() | (df[col].astype(str).str.strip() == "")
    cleaned = df[~invalid].reset_index(drop=True)
    # Fill NaN in string fields with '' (ExcelProvider does the same before Pydantic validation)
    _string_cols = ["isic", "country", "region", "sector",
                    "industry_level_1", "industry_level_2",
                    "industry_level_3", "industry_level_4"]
    for col in _string_cols:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna("")
    # Coerce numeric columns — turn junk text into NaN (Pydantic accepts NaN for Optional[float])
    _numeric_cols = [
        "ghg_s1", "ghg_s2", "ghg_s1s2", "ghg_s3",
        "company_revenue", "company_market_cap",
        "company_enterprise_value", "company_total_assets",
        "company_cash_equivalents",
    ] + [f"ghg_s3_{i}" for i in range(1, 16)]
    for col in _numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    # Coerce boolean field — junk text becomes default False
    if "sbti_validated" in cleaned.columns:
        cleaned["sbti_validated"] = cleaned["sbti_validated"].map(
            lambda v: bool(v) if isinstance(v, (bool, int, float)) and pd.notna(v) else False
        )
    return cleaned, int(invalid.sum())


def clean_target_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Validate and clean a targets DataFrame.

    - Drops rows missing required string fields (company_id, target_type, scope).
    - Coerces required integer fields (base_year, end_year) and drops rows
      where they are not valid integers.

    Returns:
        Tuple of (cleaned DataFrame, number of rows dropped).
    """
    if df.empty:
        return df, 0
    invalid = pd.Series(False, index=df.index)
    # Required string fields for IDataProviderTarget
    for col in ("company_id", "target_type", "scope"):
        if col in df.columns:
            invalid |= df[col].isna() | (df[col].astype(str).str.strip() == "")
    # Required integer fields
    for col in ("base_year", "end_year"):
        if col in df.columns:
            numeric_vals = pd.to_numeric(df[col], errors="coerce")
            invalid |= numeric_vals.isna()
    cleaned = df[~invalid].reset_index(drop=True)
    return cleaned, int(invalid.sum())


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
    
    provider_path = os.path.join(data_dir, "data_provider_example2.xlsx")
    portfolio_path = os.path.join(data_dir, "example_portfolio2.csv")
    
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
    df = pd.read_csv(file_path, encoding="iso-8859-1")
    cleaned, _ = clean_portfolio_df(df)
    return cleaned

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
        cleaned, _ = clean_portfolio_df(df)
        return cleaned
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
    cleaned, _ = clean_portfolio_df(portfolio_df)
    return ITR.utils.dataframe_to_portfolio(cleaned)


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


# ---------------------------------------------------------------------------
# Provider DataFrame extraction / reconstruction
# ---------------------------------------------------------------------------

def extract_provider_dataframes(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Read the provider Excel file and return its sheets as DataFrames.

    Returns:
        Dict with keys 'fundamental_data' and 'target_data'.
    """
    sheets = pd.read_excel(file_path, sheet_name=None, skiprows=0)
    return {
        "fundamental_data": sheets.get("fundamental_data", pd.DataFrame()),
        "target_data": sheets.get("target_data", pd.DataFrame()),
    }


def create_provider_from_dataframes(
    fundamental_df: pd.DataFrame,
    target_df: pd.DataFrame,
) -> ExcelProvider:
    """
    Reconstruct an ExcelProvider from (possibly edited) DataFrames
    by writing them into a temporary Excel file.

    Args:
        fundamental_df: Company fundamentals data.
        target_df: Target data.

    Returns:
        ExcelProvider instance ready for scoring.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp_path = tmp.name
    tmp.close()
    try:
        # Defensive cleaning before writing to Excel for ExcelProvider
        fundamental_df, _ = clean_fundamental_df(fundamental_df)
        target_df, _ = clean_target_df(target_df)
        with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
            fundamental_df.to_excel(writer, sheet_name="fundamental_data", index=False)
            target_df.to_excel(writer, sheet_name="target_data", index=False)
        provider = ExcelProvider(path=tmp_path)

        # Excel round-trip converts "" → empty cell → NaN.  ExcelProvider's
        # get_company_data fills *most* string columns but misses 'region'.
        # Patch all string fields so Pydantic doesn't reject NaN-as-float.
        _str_cols = [
            "isic", "country", "region", "sector",
            "industry_level_1", "industry_level_2",
            "industry_level_3", "industry_level_4",
        ]
        fund = provider.data["fundamental_data"]
        for col in _str_cols:
            if col in fund.columns:
                fund[col] = fund[col].fillna("")

        return provider
    finally:
        # ExcelProvider reads everything into memory, so we can clean up
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Database convenience wrappers (used by app.py)
# ---------------------------------------------------------------------------

def save_data_to_db(
    name: str,
    portfolio_df: pd.DataFrame,
    fundamental_df: pd.DataFrame,
    target_df: pd.DataFrame,
    description: str = "",
) -> None:
    """Save a complete dataset (portfolio + provider) to the local SQLite DB."""
    save_dataset(name, portfolio_df, fundamental_df, target_df, description)


def load_data_from_db(name: str) -> Dict[str, pd.DataFrame]:
    """
    Load a named dataset from the local SQLite DB.

    Returns:
        Dict with keys 'portfolio', 'fundamental_data', 'target_data'.
    """
    return load_dataset(name)


def get_saved_datasets():
    """Return list of dataset metadata dicts from the database."""
    return list_datasets()


def delete_saved_dataset(name: str) -> None:
    """Delete a named dataset from the database."""
    delete_dataset(name)
