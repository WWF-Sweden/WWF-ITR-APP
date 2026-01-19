"""
Visualization utilities for WWF ITR Tool.
Handles plotting heatmaps, charts, and contribution analysis.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional, Tuple

from ITR.interfaces import ETimeFrames, EScope


def plot_heatmap(
    aggregated_scores,
    time_frame: ETimeFrames,
    scope: EScope,
    grouping: List[str],
    title: str = "Temperature Score Heatmap",
) -> go.Figure:
    """
    Create a heatmap showing temperature scores by group.
    
    Args:
        aggregated_scores: Aggregated portfolio scores
        time_frame: Timeframe to display
        scope: Scope to display
        grouping: List of grouping columns (e.g., ['sector', 'region'])
        title: Chart title
        
    Returns:
        Plotly Figure object
    """
    try:
        tf_key = time_frame.name.lower()
        scope_key = scope.name.lower()
        
        # Extract grouped data
        data = aggregated_scores.dict()
        grouped_data = data.get(tf_key, {}).get(scope_key, {}).get('grouped', {})
        
        if not grouped_data:
            return _empty_figure("No data available for selected parameters")
        
        # Parse group names and scores
        rows = []
        for group_name, group_info in grouped_data.items():
            if '-' in group_name and len(grouping) == 2:
                parts = group_name.rsplit('-', 1)
                row = {
                    grouping[0]: parts[0],
                    grouping[1]: parts[1] if len(parts) > 1 else 'Unknown',
                    'score': group_info.get('score', np.nan) if group_info else np.nan,
                }
            else:
                row = {
                    grouping[0]: group_name,
                    'score': group_info.get('score', np.nan) if group_info else np.nan,
                }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        if len(grouping) == 2:
            # Create pivot table for heatmap
            pivot = df.pivot_table(
                index=grouping[0],
                columns=grouping[1],
                values='score',
                aggfunc='mean'
            )
            
            fig = px.imshow(
                pivot,
                labels=dict(x=grouping[1], y=grouping[0], color="Temperature (°C)"),
                color_continuous_scale='RdYlGn_r',
                aspect='auto',
                title=title,
            )
            fig.update_layout(
                xaxis_title=grouping[1].title(),
                yaxis_title=grouping[0].title(),
            )
        else:
            # Single grouping - create bar chart instead
            fig = px.bar(
                df.sort_values('score', ascending=False),
                x=grouping[0],
                y='score',
                color='score',
                color_continuous_scale='RdYlGn_r',
                title=title,
            )
            fig.update_layout(
                xaxis_title=grouping[0].title(),
                yaxis_title="Temperature Score (°C)",
            )
        
        return fig
        
    except Exception as e:
        return _empty_figure(f"Error creating heatmap: {str(e)}")


def plot_sector_statistics(
    company_contributions: pd.DataFrame,
    sector_column: str = 'sector',
    title: str = "Sector Analysis",
) -> Tuple[go.Figure, go.Figure]:
    """
    Create pie charts for sector AUM and temperature score contribution.
    
    Args:
        company_contributions: DataFrame with company contributions
        sector_column: Column name for sector grouping
        title: Chart title prefix
        
    Returns:
        Tuple of (pie_chart_figure, bar_chart_figure)
    """
    if company_contributions.empty:
        empty = _empty_figure("No data available")
        return empty, empty
    
    # Aggregate by sector
    sector_agg = company_contributions.groupby(sector_column).agg({
        'investment_value': 'sum',
        'contribution': 'sum',
        'temperature_score': 'mean',
    }).reset_index()
    
    # Pie chart for AUM distribution
    fig_pie = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'pie'}, {'type': 'pie'}]],
        subplot_titles=('Portfolio Weight (AUM)', 'Temperature Score Contribution')
    )
    
    total_investment = sector_agg['investment_value'].sum()
    sector_agg['aum_pct'] = (sector_agg['investment_value'] / total_investment) * 100
    
    fig_pie.add_trace(
        go.Pie(
            labels=sector_agg[sector_column],
            values=sector_agg['aum_pct'],
            name="AUM",
            hole=0.3,
        ),
        row=1, col=1
    )
    
    fig_pie.add_trace(
        go.Pie(
            labels=sector_agg[sector_column],
            values=sector_agg['contribution'],
            name="Contribution",
            hole=0.3,
        ),
        row=1, col=2
    )
    
    fig_pie.update_layout(title_text=f"{title} - Distribution")
    
    # Bar chart for temperature scores
    sector_agg_sorted = sector_agg.sort_values('temperature_score', ascending=False)
    
    fig_bar = px.bar(
        sector_agg_sorted,
        x=sector_column,
        y='temperature_score',
        color='temperature_score',
        color_continuous_scale='RdYlGn_r',
        title=f"{title} - Temperature Scores by Sector",
        labels={'temperature_score': 'Temperature Score (°C)'},
    )
    
    # Add reference line at 2.0°C
    fig_bar.add_hline(
        y=2.0, 
        line_dash="dash", 
        line_color="orange",
        annotation_text="2.0°C Target"
    )
    
    # Add reference line at 1.5°C
    fig_bar.add_hline(
        y=1.5, 
        line_dash="dash", 
        line_color="green",
        annotation_text="1.5°C Target"
    )
    
    return fig_pie, fig_bar


def plot_company_contributions(
    company_contributions: pd.DataFrame,
    top_n: int = 10,
    title: str = "Top Contributing Companies",
) -> go.Figure:
    """
    Create bar chart of top contributing companies.
    
    Args:
        company_contributions: DataFrame with company contributions
        top_n: Number of top companies to display
        title: Chart title
        
    Returns:
        Plotly Figure object
    """
    if company_contributions.empty:
        return _empty_figure("No data available")
    
    df = company_contributions.head(top_n).copy()
    
    fig = go.Figure()
    
    # Add contribution bars
    fig.add_trace(go.Bar(
        name='Contribution (%)',
        x=df['company_name'],
        y=df['contribution'],
        marker_color='steelblue',
        yaxis='y',
    ))
    
    # Add temperature score line
    fig.add_trace(go.Scatter(
        name='Temperature Score (°C)',
        x=df['company_name'],
        y=df['temperature_score'],
        mode='lines+markers',
        marker=dict(color='red', size=10),
        line=dict(color='red', width=2),
        yaxis='y2',
    ))
    
    fig.update_layout(
        title=title,
        xaxis=dict(title='Company', tickangle=45),
        yaxis=dict(title='Contribution (%)', side='left'),
        yaxis2=dict(
            title='Temperature Score (°C)',
            side='right',
            overlaying='y',
            range=[0, 4],
        ),
        legend=dict(x=0.5, y=1.1, orientation='h'),
        barmode='group',
    )
    
    return fig


def plot_scenario_comparison(
    original_scores: pd.DataFrame,
    scenario_scores: pd.DataFrame,
    group_column: str = 'sector',
    title: str = "Scenario Impact Analysis",
) -> go.Figure:
    """
    Create comparison chart between original and scenario scores.
    
    Args:
        original_scores: DataFrame with original temperature scores
        scenario_scores: DataFrame with scenario temperature scores
        group_column: Column to group by
        title: Chart title
        
    Returns:
        Plotly Figure object
    """
    # Aggregate by group
    original_agg = original_scores.groupby(group_column)['temperature_score'].mean().reset_index()
    original_agg.columns = [group_column, 'original_score']
    
    scenario_agg = scenario_scores.groupby(group_column)['temperature_score'].mean().reset_index()
    scenario_agg.columns = [group_column, 'scenario_score']
    
    merged = original_agg.merge(scenario_agg, on=group_column, how='outer')
    merged['change'] = merged['scenario_score'] - merged['original_score']
    merged = merged.sort_values('original_score', ascending=False)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Original Score',
        x=merged[group_column],
        y=merged['original_score'],
        marker_color='coral',
    ))
    
    fig.add_trace(go.Bar(
        name='Scenario Score',
        x=merged[group_column],
        y=merged['scenario_score'],
        marker_color='lightgreen',
    ))
    
    fig.update_layout(
        title=title,
        xaxis=dict(title=group_column.title(), tickangle=45),
        yaxis=dict(title='Temperature Score (°C)'),
        barmode='group',
        legend=dict(x=0.5, y=1.1, orientation='h'),
    )
    
    # Add reference lines
    fig.add_hline(y=1.5, line_dash="dash", line_color="green", annotation_text="1.5°C")
    fig.add_hline(y=2.0, line_dash="dash", line_color="orange", annotation_text="2.0°C")
    
    return fig


def plot_portfolio_summary_metrics(
    portfolio_score: float,
    coverage: float,
    target_score: float = 1.5,
) -> go.Figure:
    """
    Create gauge charts for portfolio summary metrics.
    
    Args:
        portfolio_score: Current portfolio temperature score
        coverage: Portfolio coverage percentage
        target_score: Target temperature score
        
    Returns:
        Plotly Figure object
    """
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}]],
        subplot_titles=('Portfolio Temperature Score', 'Portfolio Coverage')
    )
    
    # Temperature gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=portfolio_score,
        delta={'reference': target_score, 'relative': False, 'increasing': {'color': 'red'}, 'decreasing': {'color': 'green'}},
        number={'suffix': '°C'},
        gauge={
            'axis': {'range': [1.0, 4.0]},
            'bar': {'color': 'darkblue'},
            'steps': [
                {'range': [1.0, 1.5], 'color': 'lightgreen'},
                {'range': [1.5, 2.0], 'color': 'yellow'},
                {'range': [2.0, 3.0], 'color': 'orange'},
                {'range': [3.0, 4.0], 'color': 'red'},
            ],
            'threshold': {
                'line': {'color': 'green', 'width': 4},
                'thickness': 0.75,
                'value': target_score
            }
        },
    ), row=1, col=1)
    
    # Coverage gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=coverage,
        number={'suffix': '%'},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': 'darkblue'},
            'steps': [
                {'range': [0, 25], 'color': 'red'},
                {'range': [25, 50], 'color': 'orange'},
                {'range': [50, 75], 'color': 'yellow'},
                {'range': [75, 100], 'color': 'lightgreen'},
            ],
        },
    ), row=1, col=2)
    
    fig.update_layout(height=300)
    
    return fig


def _empty_figure(message: str) -> go.Figure:
    """Create an empty figure with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
