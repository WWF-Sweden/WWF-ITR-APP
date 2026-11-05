"""
Scenario analysis utilities for WWF ITR Tool.
Handles what-if scenarios and engagement modeling.
"""
import pandas as pd
from collections import OrderedDict
from datetime import datetime
import hashlib
from pathlib import Path
import pickle
from typing import List, Optional

import ITR
from ITR.temperature_score import TemperatureScore, Scenario, ScenarioType, EngagementType
from ITR.configs import TemperatureScoreConfig
from ITR.portfolio_aggregation import PortfolioAggregationMethod
from ITR.interfaces import ETimeFrames, EScope
from ITR.data.excel import ExcelProvider
from utils.cta import temperature_cta_context


# Scenario type options for UI
SCENARIO_TYPE_OPTIONS = {
    "All companies set targets (1.75°C)": ScenarioType.TARGETS,
    "All companies set SBTi targets (1.5°C)": ScenarioType.APPROVED_TARGETS,
    "Top contributors set targets (1.75°C)": ScenarioType.HIGHEST_CONTRIBUTORS,
    "Top contributors set SBTi targets (1.5°C)": ScenarioType.HIGHEST_CONTRIBUTORS_APPROVED,
}

ENGAGEMENT_TYPE_OPTIONS = {
    "Set Targets (1.75°C - Well Below 2°C)": EngagementType.SET_TARGETS,
    "Set SBTi Targets (1.5°C)": EngagementType.SET_SBTI_TARGETS,
}

# Private to each supplied session. The byte budget covers serialized results,
# not the entire Python process or the currently displayed analysis.
SCENARIO_CACHE_MAX_ENTRIES = 3
SCENARIO_CACHE_MAX_BYTES = 32 * 1024 * 1024


def get_scenario_options() -> dict:
    """Return scenario type options for UI dropdowns."""
    return SCENARIO_TYPE_OPTIONS


def get_engagement_options() -> dict:
    """Return engagement type options for UI dropdowns."""
    return ENGAGEMENT_TYPE_OPTIONS


def create_scenario(
    scenario_type: ScenarioType,
    engagement_type: EngagementType,
    aggregation_method: PortfolioAggregationMethod,
    grouping: Optional[str] = None,
) -> Scenario:
    """
    Create a scenario configuration.
    
    Args:
        scenario_type: Type of scenario to run
        engagement_type: Type of engagement
        aggregation_method: Aggregation method
        grouping: Optional grouping column
        
    Returns:
        Configured Scenario object
    """
    scenario = Scenario()
    scenario.scenario_type = scenario_type
    scenario.engagement_type = engagement_type
    scenario.aggregation_method = aggregation_method
    if grouping:
        scenario.grouping = grouping
    return scenario


def run_scenario_analysis(
    _provider: ExcelProvider,
    portfolio_df: pd.DataFrame,
    engagement_company_ids: List[str],
    scenario_type: ScenarioType,
    engagement_type: EngagementType,
    time_frames: List[ETimeFrames],
    scopes: List[EScope],
    aggregation_method: PortfolioAggregationMethod,
    grouping: Optional[List[str]] = None,
    sbti_factor: float = 1.0,
    cta_file_path: Optional[str] = None,
    cta_hash: Optional[str] = None,
    session_state=None,
) -> tuple:
    """Calculate a scenario, optionally reusing a bounded session-owned result.

    Keys include the complete provider tables and portfolio (including schema
    and index), every scenario argument, CTA contents and the calculation year.
    Standalone callers without session state always calculate afresh.
    """
    kwargs = dict(
        _provider=_provider, portfolio_df=portfolio_df,
        engagement_company_ids=engagement_company_ids, scenario_type=scenario_type,
        engagement_type=engagement_type, time_frames=time_frames, scopes=scopes,
        aggregation_method=aggregation_method, grouping=grouping,
        sbti_factor=sbti_factor, cta_file_path=cta_file_path, cta_hash=cta_hash,
    )
    # Without an explicit CTA file, SBTi enrichment can depend on an external
    # default snapshot. Do not reuse results whose source cannot be fingerprinted.
    if session_state is None or (sbti_factor != 1.0 and cta_file_path is None):
        return _calculate_scenario_analysis(**kwargs)

    cta_contents = (
        hashlib.sha256(Path(cta_file_path).read_bytes()).digest()
        if cta_file_path is not None else None
    )
    provider_config = getattr(_provider, "c", None)
    column_mapping = tuple(
        (name, getattr(provider_config, name))
        for name in dir(provider_config) if name.isupper()
    )
    inputs = (
        type(_provider).__module__, type(_provider).__qualname__, column_mapping,
        _provider.data, portfolio_df, tuple(engagement_company_ids), scenario_type,
        engagement_type, tuple(time_frames), tuple(scopes), aggregation_method,
        tuple(grouping) if grouping is not None else None, sbti_factor,
        cta_file_path, cta_hash, cta_contents, datetime.now().year,
    )
    key = hashlib.sha256(pickle.dumps(inputs, protocol=5)).digest()
    cache = session_state.setdefault("_scenario_cache", OrderedDict())
    if key in cache:
        cache.move_to_end(key)
        # These bytes are created only by this function from calculation outputs;
        # uploaded pickle files or externally supplied serialized data are never read.
        return pickle.loads(cache[key])

    result = _calculate_scenario_analysis(**kwargs)
    payload = pickle.dumps(result, protocol=5)
    if len(payload) <= SCENARIO_CACHE_MAX_BYTES:
        while cache and (
            len(cache) >= SCENARIO_CACHE_MAX_ENTRIES
            or sum(map(len, cache.values())) + len(payload) > SCENARIO_CACHE_MAX_BYTES
        ):
            cache.popitem(last=False)
        cache[key] = payload
    return result


def _calculate_scenario_analysis(
    _provider: ExcelProvider,
    portfolio_df: pd.DataFrame,
    engagement_company_ids: List[str],
    scenario_type: ScenarioType,
    engagement_type: EngagementType,
    time_frames: List[ETimeFrames],
    scopes: List[EScope],
    aggregation_method: PortfolioAggregationMethod,
    grouping: Optional[List[str]] = None,
    sbti_factor: float = 1.0,
    cta_file_path: Optional[str] = None,
    cta_hash: Optional[str] = None,
) -> tuple:
    """
    Run a what-if scenario analysis.
    
    Args:
        _provider: ExcelProvider with data
        portfolio_df: Portfolio DataFrame
        engagement_company_ids: List of company IDs to engage with
        scenario_type: Type of scenario
        engagement_type: Type of engagement
        time_frames: Timeframes to analyze
        scopes: Scopes to analyze
        aggregation_method: Aggregation method
        grouping: Optional grouping columns
        
    Returns:
        Tuple of (scenario_portfolio, scenario_aggregated)
    """
    # Create scenario portfolio with engagement targets
    scenario_portfolio = portfolio_df.copy()
    
    # Set engagement_target column
    if 'engagement_target' not in scenario_portfolio.columns:
        scenario_portfolio['engagement_target'] = False
    
    for company_id in engagement_company_ids:
        scenario_portfolio.loc[
            scenario_portfolio['company_id'] == company_id, 
            'engagement_target'
        ] = True
    
    # Create scenario
    scenario = create_scenario(
        scenario_type=scenario_type,
        engagement_type=engagement_type,
        aggregation_method=aggregation_method,
        grouping=grouping[0] if grouping and len(grouping) > 0 else None,
    )
    
    # Calculate scenario scores
    # NOTE: scenario must be passed to the constructor (not set afterwards)
    # because ScenarioType.TARGETS modifies self.default_score during
    # __init__ — assigning the scenario after construction misses this.
    #
    # Ensure all prerequisite scopes are present so the ITR library's
    # _prepare_data / _calculate_s1s2_score don't fail on partial scope sets.
    _scopes = list(scopes)
    if EScope.S1S2 in _scopes:
        if EScope.S1 not in _scopes:
            _scopes.append(EScope.S1)
        if EScope.S2 not in _scopes:
            _scopes.append(EScope.S2)
    if EScope.S1S2S3 in _scopes:
        if EScope.S1S2 not in _scopes:
            _scopes.append(EScope.S1S2)
        if EScope.S3 not in _scopes:
            _scopes.append(EScope.S3)
        if EScope.S1 not in _scopes:
            _scopes.append(EScope.S1)
        if EScope.S2 not in _scopes:
            _scopes.append(EScope.S2)

    class ScoreConfig(TemperatureScoreConfig):
        SBTI_FACTOR = sbti_factor

    ts_kwargs = dict(
        time_frames=time_frames,
        scopes=_scopes,
        aggregation_method=aggregation_method,
        grouping=grouping,
        scenario=scenario,
        config=ScoreConfig,
    )
    if sbti_factor != 1.0 and cta_file_path is not None:
        ts_kwargs["cta_file_path"] = cta_file_path

    temperature_score = TemperatureScore(**ts_kwargs)
    
    scenario_companies = ITR.utils.dataframe_to_portfolio(scenario_portfolio)
    with temperature_cta_context(cta_file_path):
        scenario_scores = temperature_score.calculate(
            data_providers=[_provider],
            portfolio=scenario_companies
        )
    scenario_aggregated = temperature_score.aggregate_scores(scenario_scores)
    
    return scenario_scores, scenario_aggregated


def calculate_scenario_impact(
    original_aggregated,
    scenario_aggregated,
    time_frame: ETimeFrames,
    scope: EScope,
) -> dict:
    """
    Calculate the impact of a scenario on portfolio scores.
    
    Args:
        original_aggregated: Original aggregated scores
        scenario_aggregated: Scenario aggregated scores
        time_frame: Timeframe to compare
        scope: Scope to compare
        
    Returns:
        Dictionary with impact metrics
    """
    try:
        tf_key = time_frame.name.lower()   # Timeframe keys are lowercase: 'mid'
        scope_key = scope.name              # Scope keys are UPPERCASE: 'S1S2S3'
        
        original_dict = original_aggregated.dict()
        scenario_dict = scenario_aggregated.dict()
        
        original_score = original_dict.get(tf_key, {}).get(scope_key, {}).get('all', {}).get('score', 0)
        scenario_score = scenario_dict.get(tf_key, {}).get(scope_key, {}).get('all', {}).get('score', 0)
        
        change = scenario_score - original_score
        pct_change = (change / original_score * 100) if original_score > 0 else 0
        
        return {
            'original_score': round(original_score, 2),
            'scenario_score': round(scenario_score, 2),
            'absolute_change': round(change, 2),
            'percent_change': round(pct_change, 2),
        }
    except Exception:
        return {
            'original_score': 0,
            'scenario_score': 0,
            'absolute_change': 0,
            'percent_change': 0,
        }


def get_engagement_candidates(
    amended_portfolio: pd.DataFrame,
    time_frame: ETimeFrames,
    scope: EScope,
    top_n: int = 20,
    min_ownership: float = 0.0,
) -> pd.DataFrame:
    """
    Identify companies that are good candidates for engagement.
    
    Args:
        amended_portfolio: Portfolio with temperature scores
        time_frame: Timeframe to analyze
        scope: Scope to analyze
        top_n: Maximum number of candidates to return
        min_ownership: Minimum ownership percentage filter
        
    Returns:
        DataFrame with engagement candidates
    """
    # Filter to specific timeframe/scope
    mask = (
        (amended_portfolio['time_frame'] == time_frame) &
        (amended_portfolio['scope'] == scope)
    )
    df = amended_portfolio.loc[mask].copy()
    
    # Calculate contribution metrics
    total_investment = df['investment_value'].sum()
    if total_investment > 0:
        df['portfolio_percentage'] = (df['investment_value'] / total_investment) * 100
    else:
        df['portfolio_percentage'] = 0
    
    # Calculate ownership if available
    if 'ownership_percentage' not in df.columns:
        df['ownership_percentage'] = 0.0
    
    # Filter by ownership
    if min_ownership > 0:
        df = df[df['ownership_percentage'] >= min_ownership]
    
    # Prioritize high temperature score companies
    df = df[df['temperature_score'] >= 2.0]  # Focus on high scorers
    
    # Sort by temperature score * portfolio weight (biggest impact potential)
    df['impact_score'] = df['temperature_score'] * df['portfolio_percentage']
    df = df.sort_values('impact_score', ascending=False)
    
    result = df[[
        'company_name',
        'company_id',
        'sector',
        'region',
        'temperature_score',
        'portfolio_percentage',
        'ownership_percentage',
        'impact_score',
    ]].head(top_n)
    
    return result.round(2)


def compare_group_scores(
    original_aggregated,
    scenario_aggregated,
    time_frame: ETimeFrames,
    scope: EScope,
) -> pd.DataFrame:
    """
    Compare group-level scores between original and scenario.
    
    Args:
        original_aggregated: Original aggregated scores
        scenario_aggregated: Scenario aggregated scores
        time_frame: Timeframe to compare
        scope: Scope to compare
        
    Returns:
        DataFrame comparing group scores
    """
    try:
        tf_key = time_frame.name.lower()   # Timeframe keys are lowercase: 'mid'
        scope_key = scope.name              # Scope keys are UPPERCASE: 'S1S2S3'
        
        original_dict = original_aggregated.dict()
        scenario_dict = scenario_aggregated.dict()
        
        original_grouped = original_dict.get(tf_key, {}).get(scope_key, {}).get('grouped', {})
        scenario_grouped = scenario_dict.get(tf_key, {}).get(scope_key, {}).get('grouped', {})
        
        rows = []
        all_groups = set(original_grouped.keys()) | set(scenario_grouped.keys())
        
        for group in all_groups:
            original_score = original_grouped.get(group, {}).get('score', None)
            scenario_score = scenario_grouped.get(group, {}).get('score', None)
            
            if original_score is not None and scenario_score is not None:
                change = scenario_score - original_score
            else:
                change = None
            
            rows.append({
                'Group': group,
                'Original Score': round(original_score, 2) if original_score else None,
                'Scenario Score': round(scenario_score, 2) if scenario_score else None,
                'Change': round(change, 2) if change else None,
            })
        
        df = pd.DataFrame(rows)
        df = df.sort_values('Original Score', ascending=False, na_position='last')
        
        return df
        
    except Exception:
        return pd.DataFrame()
