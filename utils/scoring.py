"""
Temperature scoring and portfolio aggregation utilities.
Handles calculation of temperature scores at company and portfolio level.
"""
import pandas as pd
import streamlit as st
from typing import List, Optional

from ITR.temperature_score import TemperatureScore, Scenario, ScenarioType, EngagementType
from ITR.portfolio_aggregation import PortfolioAggregationMethod
from ITR.portfolio_coverage_tvp import PortfolioCoverageTVP
from ITR.interfaces import ETimeFrames, EScope
from ITR.data.excel import ExcelProvider


# Mapping for UI display names
TIMEFRAME_OPTIONS = {
    "SHORT": ETimeFrames.SHORT,
    "MID": ETimeFrames.MID,
    "LONG": ETimeFrames.LONG,
}

SCOPE_OPTIONS = {
    "Scope 1": EScope.S1,
    "Scope 2": EScope.S2,
    "Scope 3": EScope.S3,
    "Scope 1+2": EScope.S1S2,
    "Scope 1+2+3": EScope.S1S2S3,
}

AGGREGATION_OPTIONS = {
    "WATS (Weighted Average)": PortfolioAggregationMethod.WATS,
    "TETS (Total Emissions)": PortfolioAggregationMethod.TETS,
    "MOTS (Market Owned)": PortfolioAggregationMethod.MOTS,
    "EOTS (Enterprise Owned)": PortfolioAggregationMethod.EOTS,
    "ECOTS (EV + Cash Owned)": PortfolioAggregationMethod.ECOTS,
    "AOTS (Assets Owned)": PortfolioAggregationMethod.AOTS,
    "ROTS (Revenue Owned)": PortfolioAggregationMethod.ROTS,
}


def get_timeframe_options() -> dict:
    """Return timeframe options for UI dropdowns."""
    return TIMEFRAME_OPTIONS


def get_scope_options() -> dict:
    """Return scope options for UI dropdowns."""
    return SCOPE_OPTIONS


def get_aggregation_options() -> dict:
    """Return aggregation method options for UI dropdowns."""
    return AGGREGATION_OPTIONS


@st.cache_data(show_spinner="Calculating temperature scores...")
def calculate_temperature_scores(
    _provider: ExcelProvider,
    _companies: list,
    time_frames: List[ETimeFrames],
    scopes: List[EScope],
    aggregation_method: PortfolioAggregationMethod,
    grouping: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Calculate temperature scores for all companies in portfolio.
    
    Args:
        _provider: ExcelProvider with fundamental/target data
        _companies: List of PortfolioCompany objects
        time_frames: List of timeframes to calculate
        scopes: List of scopes to calculate
        aggregation_method: Method for aggregating scores
        grouping: Optional list of columns to group by
        
    Returns:
        DataFrame with amended portfolio including temperature scores
    """
    temperature_score = TemperatureScore(
        time_frames=time_frames,
        scopes=scopes,
        aggregation_method=aggregation_method,
        grouping=grouping,
    )
    
    amended_portfolio = temperature_score.calculate(
        data_providers=[_provider],
        portfolio=_companies
    )
    
    return amended_portfolio


def aggregate_portfolio_scores(
    amended_portfolio: pd.DataFrame,
    time_frames: List[ETimeFrames],
    scopes: List[EScope],
    aggregation_method: PortfolioAggregationMethod,
    grouping: Optional[List[str]] = None,
):
    """
    Aggregate company scores to portfolio level.
    
    Args:
        amended_portfolio: DataFrame with company temperature scores
        time_frames: List of timeframes
        scopes: List of scopes
        aggregation_method: Method for aggregating scores
        grouping: Optional grouping columns
        
    Returns:
        ScoreAggregation object with portfolio scores
    """
    temperature_score = TemperatureScore(
        time_frames=time_frames,
        scopes=scopes,
        aggregation_method=aggregation_method,
        grouping=grouping,
    )
    
    return temperature_score.aggregate_scores(amended_portfolio)


def get_aggregated_scores_df(aggregated_scores) -> pd.DataFrame:
    """
    Convert ScoreAggregation object to readable DataFrame.
    
    Args:
        aggregated_scores: ScoreAggregation object
        
    Returns:
        DataFrame with scores by timeframe/scope
    """
    df_agg = pd.DataFrame(aggregated_scores.dict()).apply(
        lambda x: x.map(
            lambda y: round(y['all']['score'], 2)
            if y is not None and y['all'] is not None and 'score' in y['all']
            else None
        )
    )
    return df_agg


def calculate_portfolio_coverage(
    amended_portfolio: pd.DataFrame,
    aggregation_method: PortfolioAggregationMethod,
) -> float:
    """
    Calculate portfolio coverage (% with SBTi targets).
    
    Args:
        amended_portfolio: DataFrame with company scores
        aggregation_method: Aggregation method to use
        
    Returns:
        Coverage percentage
    """
    portfolio_coverage_tvp = PortfolioCoverageTVP()
    coverage = portfolio_coverage_tvp.get_portfolio_coverage(
        amended_portfolio.copy(),
        aggregation_method
    )
    return coverage


def get_company_scores_summary(
    amended_portfolio: pd.DataFrame,
    time_frame: ETimeFrames = ETimeFrames.MID,
    scope: EScope = EScope.S1S2,
) -> pd.DataFrame:
    """
    Get summary of company scores for specific timeframe/scope.
    
    Args:
        amended_portfolio: DataFrame with all scores
        time_frame: Timeframe to filter by
        scope: Scope to filter by
        
    Returns:
        DataFrame with company scores
    """
    mask = (
        (amended_portfolio['time_frame'] == time_frame) &
        (amended_portfolio['scope'] == scope)
    )
    
    return amended_portfolio.loc[mask, [
        'company_name', 
        'company_id', 
        'sector',
        'region',
        'temperature_score',
        'investment_value',
    ]].copy()


def get_contributions_per_group(
    aggregated_scores,
    time_frame: ETimeFrames,
    scope: EScope,
    group_name: str,
) -> pd.DataFrame:
    """
    Get company contributions for a specific group.
    
    Args:
        aggregated_scores: Aggregated portfolio scores
        time_frame: Timeframe to analyze
        scope: Scope to analyze
        group_name: Name of the group (e.g., "Industrials-Europe")
        
    Returns:
        DataFrame with company contributions
    """
    # Access the grouped scores from aggregated data
    try:
        tf_key = time_frame.name.lower()
        scope_key = scope.name.lower()
        
        group_data = aggregated_scores.dict()[tf_key]
        if group_data and scope_key in group_data:
            contributions = group_data[scope_key].get('grouped', {}).get(group_name, {})
            if contributions:
                return pd.DataFrame(contributions.get('contributions', []))
    except Exception:
        pass
    
    return pd.DataFrame()


def collect_company_contributions(
    aggregated_portfolio,
    amended_portfolio: pd.DataFrame,
    time_frame: ETimeFrames,
    scope: EScope,
) -> pd.DataFrame:
    """
    Collect company-level contributions to portfolio score.
    
    Args:
        aggregated_portfolio: Aggregated portfolio scores
        amended_portfolio: DataFrame with company scores
        time_frame: Timeframe to analyze
        scope: Scope to analyze
        
    Returns:
        DataFrame with contributions
    """
    # Filter to specific timeframe/scope
    mask = (
        (amended_portfolio['time_frame'] == time_frame) &
        (amended_portfolio['scope'] == scope)
    )
    df = amended_portfolio.loc[mask].copy()
    
    # Calculate contributions based on investment value
    total_investment = df['investment_value'].sum()
    if total_investment > 0:
        df['portfolio_percentage'] = (df['investment_value'] / total_investment) * 100
        df['contribution'] = (
            df['temperature_score'] * df['investment_value'] / 
            (df['temperature_score'] * df['investment_value']).sum()
        ) * 100
    else:
        df['portfolio_percentage'] = 0
        df['contribution'] = 0
    
    # Sort by contribution descending
    df = df.sort_values('contribution', ascending=False)
    
    return df
