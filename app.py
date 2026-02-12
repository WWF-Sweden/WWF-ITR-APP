"""
WWF Finance Tool - Temperature Scoring & Portfolio Coverage
Streamlit Application

This app allows users to analyze portfolios' and companies' GHG emissions
reduction targets using the CDP-WWF Temperature Scoring Methodology.
"""
import streamlit as st
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import ITR modules
import ITR
from ITR.interfaces import ETimeFrames, EScope
from ITR.portfolio_aggregation import PortfolioAggregationMethod

# Import local utilities
from utils.data_loader import (
    download_sample_data,
    load_provider_data,
    load_portfolio_data,
    load_uploaded_provider_file,
    load_uploaded_portfolio_file,
    convert_portfolio_to_companies,
    validate_portfolio_data,
)
from utils.scoring import (
    get_timeframe_options,
    get_scope_options,
    get_aggregation_options,
    calculate_temperature_scores,
    aggregate_portfolio_scores,
    get_aggregated_scores_df,
    calculate_portfolio_coverage,
    collect_company_contributions,
)
from utils.visualization import (
    plot_heatmap,
    plot_sector_statistics,
    plot_company_contributions,
    plot_scenario_comparison,
    plot_portfolio_summary_metrics,
)
from utils.scenarios import (
    get_scenario_options,
    get_engagement_options,
    run_scenario_analysis,
    calculate_scenario_impact,
    get_engagement_candidates,
    compare_group_scores,
)

from utils.data_source import select_data_source, validate_data, data_preview

# Page configuration
st.set_page_config(
    page_title="WWF ITR Tool",
    page_icon="assets/favicon.png",  # Can also use an emoji like "🌍" or a URL
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main application entry point."""
    
    # Header with logo
    col1, col2 = st.columns([1, 10])
    with col1:
        # Add your logo image here (e.g., WWF panda logo)
        st.image("assets/panda.jpg", width=80)
        # st.markdown("🌍")  # Temporary placeholder - replace with st.image() above
    with col2:
        st.title("WWF Finance Tool")
        st.subheader("Temperature Scoring & Portfolio Coverage")
    
    st.markdown("""
    Analyze your portfolio's alignment with climate goals using the 
    [CDP-WWF Temperature Scoring Methodology](https://wwfint.awsassets.panda.org/downloads/cdp-wwf-temperature-scoring-methodology---september-2024.pdf).
    """)
    
    # Sidebar - Data Configuration
    with st.sidebar:
        st.header("📊 Data Configuration")
        
        data_source = st.radio(
            "Data Source",
            options=["Sample Data", "Upload Custom Data"],
            index=0,
            help="Choose sample data for testing or upload your own files"
        )
        
        if data_source == "Sample Data":
            provider_path, portfolio_path = download_sample_data()
            provider = load_provider_data(provider_path)
            portfolio_df = load_portfolio_data(portfolio_path)
            st.success("✅ Sample data loaded")
        else:
            st.markdown("#### Provider Data (Excel)")
            uploaded_provider = st.file_uploader(
                "Upload fundamental & target data",
                type=["xlsx", "xls"],
                key="provider_file",
                help="Excel file with company fundamentals and targets"
            )
            
            st.markdown("#### Portfolio Data (CSV)")
            uploaded_portfolio = st.file_uploader(
                "Upload portfolio data",
                type=["csv"],
                key="portfolio_file",
                help="CSV file with company_id and investment_value columns"
            )
            
            if uploaded_provider is None or uploaded_portfolio is None:
                st.warning("⚠️ Please upload both files to continue")
                st.stop()
            
            provider_path = load_uploaded_provider_file(uploaded_provider)
            provider = load_provider_data(provider_path)
            portfolio_df = load_uploaded_portfolio_file(uploaded_portfolio)
            
            # Validate portfolio
            is_valid, missing = validate_portfolio_data(portfolio_df)
            if not is_valid:
                st.error(f"❌ Missing required columns: {', '.join(missing)}")
                st.stop()
            
            st.success("✅ Custom data loaded")
        
        st.divider()
        
        # Analysis Parameters
        st.header("⚙️ Analysis Parameters")
        
        # Timeframe selection
        timeframe_options = get_timeframe_options()
        selected_timeframes = st.multiselect(
            "Timeframes",
            options=list(timeframe_options.keys()),
            default=["MID"],
            help="Select one or more timeframes for analysis"
        )
        time_frames = [timeframe_options[tf] for tf in selected_timeframes]
        
        if not time_frames:
            st.warning("Please select at least one timeframe")
            st.stop()
        
        # Scope selection
        scope_options = get_scope_options()
        selected_scopes = st.multiselect(
            "Scopes",
            options=list(scope_options.keys()),
            default=["Scope 1+2", "Scope 1+2+3"],
            help="Select GHG emission scopes"
        )
        scopes = [scope_options[s] for s in selected_scopes]
        
        if not scopes:
            st.warning("Please select at least one scope")
            st.stop()
        
        # Aggregation method
        agg_options = get_aggregation_options()
        selected_agg = st.selectbox(
            "Aggregation Method",
            options=list(agg_options.keys()),
            index=0,
            help="Method for aggregating company scores to portfolio level"
        )
        aggregation_method = agg_options[selected_agg]
        
        # Grouping options
        st.markdown("#### Grouping")
        grouping_options = ["None", "sector", "region", "sector + region"]
        selected_grouping = st.selectbox(
            "Group by",
            options=grouping_options,
            index=0,
            help="Group companies for analysis"
        )
        
        if selected_grouping == "None":
            grouping = None
        elif selected_grouping == "sector + region":
            grouping = ["sector", "region"]
        else:
            grouping = [selected_grouping]
        
        st.divider()
        
        # Copyright and Disclaimer
        st.markdown("""
        <div style='font-size: 0.8em; color: #666;'>
        <p><strong>© WWF Sweden, 2026</strong></p>
        <p><em>Disclaimer:</em> This tool provides temperature scores based on the CDP-WWF Temperature Scoring Methodology v1.5. Results are for informational purposes only and should not be considered as financial or investment advice.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Convert portfolio to companies
    companies = convert_portfolio_to_companies(portfolio_df)
    # Add confirmation before running calculations
    st.markdown("---")
    
    col_img, col_header = st.columns([1, 12])
    with col_img:
        st.image("assets/itr-logo.png", width=64)
    with col_header:
        st.subheader("Ready to Calculate Temperature Scores")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.info(f"**Data loaded:** {len(portfolio_df)} companies")
        st.info(f"**Source:** {data_source}")
    with col2:
        st.markdown("")
    with col3:
        if 'calculation_run' not in st.session_state:
            st.session_state.calculation_run = False
        
        if st.button("▶️ Run Analysis", type="primary", use_container_width=True):
            st.session_state.calculation_run = True
        
        if st.session_state.calculation_run:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.calculation_run = False
                st.rerun()
    
    if not st.session_state.calculation_run:
        st.warning("⏳ Click **Run Analysis** to calculate temperature scores")
        st.stop()
    
    st.markdown("---")
    
    
    # Calculate temperature scores
    with st.spinner("Calculating temperature scores..."):
        amended_portfolio = calculate_temperature_scores(
            _provider=provider,
            _companies=companies,
            time_frames=time_frames,
            scopes=scopes,
            aggregation_method=aggregation_method,
            grouping=grouping,
        )
        
        aggregated_scores = aggregate_portfolio_scores(
            amended_portfolio=amended_portfolio,
            time_frames=time_frames,
            scopes=scopes,
            aggregation_method=aggregation_method,
            grouping=grouping,
        )
        
        coverage = calculate_portfolio_coverage(amended_portfolio, aggregation_method)
        
        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Portfolio Overview",
            "🔥 Hotspot Analysis", 
            "🏢 Company Analysis",
            "🎯 What-If Scenarios",
            "📥 Export Data"
        ])
        
        # Tab 1: Portfolio Overview
        with tab1:
            st.header("Portfolio Temperature Score Overview")
            
            # Get primary score for display with preference logic
            # Scope preference: S1S2S3 > S1S2
            preferred_scope_order = [EScope.S1S2S3, EScope.S1S2]
            primary_scope = None
            for pref_scope in preferred_scope_order:
                if pref_scope in scopes:
                    primary_scope = pref_scope
                    break
            if primary_scope is None:
                primary_scope = scopes[0] if scopes else EScope.S1S2S3
            
            # Timeframe preference: MID > SHORT > LONG
            preferred_tf_order = [ETimeFrames.MID, ETimeFrames.SHORT, ETimeFrames.LONG]
            primary_tf = None
            for pref_tf in preferred_tf_order:
                if pref_tf in time_frames:
                    primary_tf = pref_tf
                    break
            if primary_tf is None:
                primary_tf = time_frames[0] if time_frames else ETimeFrames.MID
            
            # Extract portfolio score with safer nested access
            portfolio_score = 3.4  # Default fallback
            try:
                tf_key = primary_tf.name.lower()  # Timeframes are lowercase: 'mid'
                scope_key = primary_scope.name  # Scopes are UPPERCASE: 'S1S2S3'
                scores_dict = aggregated_scores.model_dump()
                
                if tf_key in scores_dict and scope_key in scores_dict[tf_key]:
                    all_scores = scores_dict[tf_key][scope_key].get('all', {})
                    portfolio_score = all_scores.get('score', portfolio_score)
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(f"Could not extract portfolio score: {e}")
                portfolio_score = 3.4
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Portfolio Temperature", f"{portfolio_score:.2f}°C")
            with col2:
                st.metric("Portfolio Coverage", f"{coverage:.1f}%")
            with col3:
                st.metric("Companies Analyzed", len(portfolio_df))
            with col4:
                target_gap = portfolio_score - 1.5
                st.metric("Gap to 1.5°C", f"{target_gap:.2f}°C", delta=f"{target_gap:.2f}", delta_color="inverse")
            
            # Display which timeframe and scope are shown
            scope_display_names = {
                'S1': 'Scope 1',
                'S2': 'Scope 2',
                'S3': 'Scope 3',
                'S1S2': 'Scope 1+2',
                'S1S2S3': 'Scope 1+2+3'
            }
            tf_display_names = {
                'SHORT': 'Short-term',
                'MID': 'Mid-term',
                'LONG': 'Long-term'
            }
            st.info(f"📊 Chart displays: **{tf_display_names.get(primary_tf.name, primary_tf.name)}** timeframe, **{scope_display_names.get(primary_scope.name, primary_scope.name)}**")
            
            # Gauge charts
            st.plotly_chart(
                plot_portfolio_summary_metrics(portfolio_score, coverage),
                use_container_width=True
            )
            
            # Score matrix
            st.subheader("Temperature Scores by Timeframe & Scope")
            scores_df = get_aggregated_scores_df(aggregated_scores)
            st.dataframe(scores_df, use_container_width=True)
            
            # Portfolio data preview
            with st.expander("📋 View Portfolio Data"):
                st.dataframe(portfolio_df.head(20), use_container_width=True)
        
        # Tab 2: Hotspot Analysis
        with tab2:
            st.header("Hotspot Analysis")
            
            if grouping:
                st.markdown(f"**Grouped by:** {', '.join(grouping)}")
                
                # Analysis parameters selection
                col1, col2 = st.columns(2)
                with col1:
                    analysis_tf = st.selectbox(
                        "Timeframe for Analysis",
                        options=selected_timeframes,
                        index=0,
                        key="hotspot_tf"
                    )
                with col2:
                    analysis_scope = st.selectbox(
                        "Scope for Analysis",
                        options=selected_scopes,
                        index=0,
                        key="hotspot_scope"
                    )
                
                analysis_time_frame = timeframe_options[analysis_tf]
                analysis_scope_val = scope_options[analysis_scope]
                
                # Heatmap
                st.subheader("Temperature Score Heatmap")
                heatmap_fig = plot_heatmap(
                    aggregated_scores=aggregated_scores,
                    time_frame=analysis_time_frame,
                    scope=analysis_scope_val,
                    grouping=grouping,
                    title=f"Temperature Scores - {analysis_tf} / {analysis_scope}"
                )
                st.plotly_chart(heatmap_fig, use_container_width=True)
            else:
                st.info("💡 Select a grouping option in the sidebar to see hotspot analysis by sector, region, etc.")
                
                # Show sector analysis even without grouping
                st.subheader("Sector Temperature Scores")
                analysis_tf = st.selectbox(
                    "Timeframe for Analysis",
                    options=selected_timeframes,
                    index=0,
                    key="sector_tf"
                )
                analysis_scope = st.selectbox(
                    "Scope for Analysis",
                    options=selected_scopes,
                    index=0,
                    key="sector_scope"
                )
                
                analysis_time_frame = timeframe_options[analysis_tf]
                analysis_scope_val = scope_options[analysis_scope]
                
                contributions = collect_company_contributions(
                    aggregated_portfolio=aggregated_scores,
                    amended_portfolio=amended_portfolio,
                    time_frame=analysis_time_frame,
                    scope=analysis_scope_val,
                )
                
                if not contributions.empty and 'sector' in contributions.columns:
                    pie_fig, bar_fig = plot_sector_statistics(contributions)
                    st.plotly_chart(pie_fig, use_container_width=True)
                    st.plotly_chart(bar_fig, use_container_width=True)
        
        # Tab 3: Company Analysis
        with tab3:
            st.header("Company Analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                company_tf = st.selectbox(
                    "Timeframe",
                    options=selected_timeframes,
                    index=0,
                    key="company_tf"
                )
            with col2:
                company_scope = st.selectbox(
                    "Scope",
                    options=selected_scopes,
                    index=0,
                    key="company_scope"
                )
            
            company_time_frame = timeframe_options[company_tf]
            company_scope_val = scope_options[company_scope]
            
            # Get company contributions
            contributions = collect_company_contributions(
                aggregated_portfolio=aggregated_scores,
                amended_portfolio=amended_portfolio,
                time_frame=company_time_frame,
                scope=company_scope_val,
            )
            
            # Top contributors chart
            st.subheader("Top Contributing Companies")
            top_n = st.slider("Number of companies to show", 5, 30, 10, key="top_n")
            
            contrib_fig = plot_company_contributions(contributions, top_n=top_n)
            st.plotly_chart(contrib_fig, use_container_width=True)
            
            # Detailed table
            st.subheader("Company Details")
            
            # Sector filter
            if 'sector' in contributions.columns:
                sectors = ["All"] + sorted(contributions['sector'].unique().tolist())
                selected_sector = st.selectbox("Filter by Sector", sectors, key="sector_filter")
                
                if selected_sector != "All":
                    display_df = contributions[contributions['sector'] == selected_sector]
                else:
                    display_df = contributions
            else:
                display_df = contributions
            
            # Display columns
            display_cols = ['company_name', 'company_id', 'sector', 'temperature_score', 
                        'contribution', 'portfolio_percentage']
            available_cols = [c for c in display_cols if c in display_df.columns]
            
            st.dataframe(
                display_df[available_cols].round(2),
                use_container_width=True,
                height=400
            )
        
        # Tab 4: What-If Scenarios
        with tab4:
            st.header("What-If Scenario Analysis")
            
            st.markdown("""
            Model the impact of engaging with portfolio companies to set climate targets.
            Select companies and scenario parameters to see how your portfolio score could improve.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Scenario Configuration")
                
                scenario_options = get_scenario_options()
                selected_scenario = st.selectbox(
                    "Scenario Type",
                    options=list(scenario_options.keys()),
                    index=3,  # Default to top contributors
                    help="Choose the type of engagement scenario"
                )
                scenario_type = scenario_options[selected_scenario]
                
                engagement_options = get_engagement_options()
                selected_engagement = st.selectbox(
                    "Engagement Type",
                    options=list(engagement_options.keys()),
                    index=0,
                    help="Target temperature for engaged companies"
                )
                engagement_type = engagement_options[selected_engagement]
                
                # Timeframe/scope for scenario
                scenario_tf = st.selectbox(
                    "Timeframe",
                    options=selected_timeframes,
                    index=0,
                    key="scenario_tf"
                )
                scenario_scope = st.selectbox(
                    "Scope",
                    options=selected_scopes,
                    index=0,
                    key="scenario_scope"
                )
            
            with col2:
                st.subheader("Engagement Candidates")
                
                scenario_time_frame = timeframe_options[scenario_tf]
                scenario_scope_val = scope_options[scenario_scope]
                
                # Get engagement candidates
                candidates = get_engagement_candidates(
                    amended_portfolio=amended_portfolio,
                    time_frame=scenario_time_frame,
                    scope=scenario_scope_val,
                    top_n=20,
                )
                
                if not candidates.empty:
                    # Multi-select for companies
                    company_options = candidates['company_name'].tolist()
                    selected_companies = st.multiselect(
                        "Select Companies to Engage",
                        options=company_options,
                        default=company_options[:3] if len(company_options) >= 3 else company_options,
                        help="Choose companies to include in the engagement scenario"
                    )
                    
                    # Get company IDs for selected companies
                    engagement_ids = candidates[
                        candidates['company_name'].isin(selected_companies)
                    ]['company_id'].tolist()
                    
                    st.dataframe(
                        candidates[candidates['company_name'].isin(selected_companies)],
                        use_container_width=True,
                        height=200
                    )
                else:
                    st.warning("No high-scoring companies found for engagement")
                    engagement_ids = []
            
            # Run scenario
            if st.button("🚀 Run Scenario Analysis", type="primary") and engagement_ids:
                with st.spinner("Running scenario analysis..."):
                    scenario_scores, scenario_aggregated = run_scenario_analysis(
                        _provider=provider,
                        portfolio_df=portfolio_df,
                        engagement_company_ids=engagement_ids,
                        scenario_type=scenario_type,
                        engagement_type=engagement_type,
                        time_frames=time_frames,
                        scopes=scopes,
                        aggregation_method=aggregation_method,
                        grouping=grouping,
                    )
                    
                    # Calculate impact
                    impact = calculate_scenario_impact(
                        original_aggregated=aggregated_scores,
                        scenario_aggregated=scenario_aggregated,
                        time_frame=scenario_time_frame,
                        scope=scenario_scope_val,
                    )
                    
                    st.success("✅ Scenario analysis complete!")
                    
                    # Display impact metrics
                    st.subheader("Scenario Impact")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Original Score", f"{impact['original_score']}°C")
                    with col2:
                        st.metric("Scenario Score", f"{impact['scenario_score']}°C")
                    with col3:
                        st.metric(
                            "Temperature Reduction",
                            f"{impact['absolute_change']}°C",
                            delta=f"{impact['percent_change']:.1f}%",
                            delta_color="inverse"
                        )
                    
                    # Comparison chart
                    if grouping:
                        comparison_df = compare_group_scores(
                            original_aggregated=aggregated_scores,
                            scenario_aggregated=scenario_aggregated,
                            time_frame=scenario_time_frame,
                            scope=scenario_scope_val,
                        )
                        
                        if not comparison_df.empty:
                            st.subheader("Group Score Comparison")
                            st.dataframe(comparison_df, use_container_width=True)
        
        # Tab 5: Export Data
        with tab5:
            st.header("Export Data")
            
            st.markdown("Download your analysis results for further processing or reporting.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Full Portfolio Data")
                st.markdown("Export complete portfolio with temperature scores")
                
                export_df = amended_portfolio.copy()
                csv = export_df.to_csv(index=False)
                
                st.download_button(
                    label="Download Portfolio CSV",
                    data=csv,
                    file_name="portfolio_temperature_scores.csv",
                    mime="text/csv",
                )
            
            with col2:
                st.subheader("📈 Aggregated Scores")
                st.markdown("Export portfolio-level aggregated scores")
                
                scores_df = get_aggregated_scores_df(aggregated_scores)
                scores_csv = scores_df.to_csv()
                
                st.download_button(
                    label="Download Scores CSV",
                    data=scores_csv,
                    file_name="aggregated_scores.csv",
                    mime="text/csv",
                )
            
            # Excel export
            st.subheader("📑 Excel Export")
            st.markdown("Export all data to a single Excel file with multiple sheets")
            
            if st.button("Generate Excel File"):
                import io
                buffer = io.BytesIO()
                
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    amended_portfolio.to_excel(writer, sheet_name='Portfolio Scores', index=False)
                    scores_df.to_excel(writer, sheet_name='Aggregated Scores')
                    portfolio_df.to_excel(writer, sheet_name='Original Portfolio', index=False)
                
                st.download_button(
                    label="Download Excel File",
                    data=buffer.getvalue(),
                    file_name="itr_analysis_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )


if __name__ == "__main__":
    main()
