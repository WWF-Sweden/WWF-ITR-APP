"""
WWF Finance Tool - Temperature Scoring & Portfolio Coverage
Streamlit Application

This app allows users to analyze portfolios' and companies' GHG emissions
reduction targets using the CDP-WWF Temperature Scoring Methodology.
"""
import hashlib
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import logging

# Deployment mode: set ITR_DEPLOYMENT=cloud in Streamlit Cloud environment settings.
# Absence of the variable is treated as local/safe (pip install, Docker, etc.).
is_cloud = os.environ.get("ITR_DEPLOYMENT") == "cloud"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import ITR modules
import ITR
from ITR.interfaces import ETimeFrames, EScope
from ITR.portfolio_aggregation import PortfolioAggregationMethod
from ITR.configs import PortfolioCoverageTVPConfig

# Import local utilities
from utils.data_loader import (
    download_sample_data,
    load_provider_data,
    load_portfolio_data,
    load_uploaded_provider_file,
    load_uploaded_portfolio_file,
    convert_portfolio_to_companies,
    validate_portfolio_data,
    extract_provider_dataframes,
    create_provider_from_dataframes,
    save_data_to_db,
    load_data_from_db,
    get_saved_datasets,
    delete_saved_dataset,
    clean_portfolio_df,
    clean_fundamental_df,
    clean_target_df,
    load_uploaded_provider_scores_file,
    validate_provider_scores_data,
    prepare_provider_scores_df,
)
from db.database import init_db
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
    
    # Load custom CSS
    with open("assets/style.css") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
    
    # Header with logo
    col1, col2 = st.columns([1, 10])
    with col1:
        # Add your logo image here (e.g., WWF panda logo)
        st.image("assets/panda.jpg", width=80)
        # st.markdown("🌍")  # Temporary placeholder - replace with st.image() above
    with col2:
        st.title("WWF ITR Tool")
        st.subheader("Temperature Scoring & Portfolio Coverage")
    
    st.markdown("""
    Analyze your portfolio's alignment with climate goals using the 
    [CDP-WWF Temperature Scoring Methodology](https://wwfint.awsassets.panda.org/downloads/cdp-wwf-temperature-scoring-methodology---september-2024.pdf).
    """)
    st.markdown("""
    For a detailed run-through of the methodology and how to use this tool, check out this 
    [Analysis Example Notebook](https://colab.research.google.com/github/WWF-Sweden/ITR-tool/blob/main/examples/1_analysis_example.ipynb).
    """)
    # Fixed footer with copyright and disclaimer
    st.markdown("""
    <style>
    .footer {
        position: fixed;
        left: 21rem;
        bottom: 0;
        right: 0;
        background-color: #1a1a1a;
        border-top: 2px solid #5bc5f2;
        padding: 8px 20px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 0.75em;
        color: #ccc;
        z-index: 999;
        text-align: left;
    }
    .footer strong {
        color: #ffffff;
    }
    .footer a {
        color: #5bc5f2;
    }
    /* Adjust footer when sidebar is collapsed */
    [data-testid="collapsedControl"] ~ div .footer {
        left: 0;
    }
    </style>
    <div class="footer">
        <strong>© WWF Sweden, 2026</strong> | 
        <em>Disclaimer:</em> This tool provides temperature scores based on the CDP-WWF Temperature Scoring Methodology v1.5. 
        Results are for informational purposes only and should not be considered as financial or investment advice.
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Data Configuration
    with st.sidebar:
        st.header("📊 Data Configuration")
        st.markdown("[📄 Data Requirements](https://wwf-sweden.github.io/ITR-tool/DataRequirements.html)")
        
        data_source = st.radio(
            "Data Source",
            options=["Sample Data", "Upload Custom Data", "Pre-scored Data (4b format)", "Load from Database"],
            index=0,
            help="Choose sample data, upload files, upload pre-scored data, or load a previously saved dataset"
        )
        
        # Clear previously loaded data when the user switches source
        if "_data_source" in st.session_state and st.session_state._data_source != data_source:
            for _key in ("data_loaded", "portfolio_df", "fundamental_df", "target_df",
                         "scoring_results", "calculation_run",
                         "edit_portfolio_mode", "edit_fundamental_mode", "edit_target_mode",
                         "provider_scores_df", "data_mode", "ps_aggregation_result"):
                st.session_state.pop(_key, None)
            st.session_state._data_source = data_source

        # -- Source-specific configuration (no data loaded yet) ----------------
        _ready_to_load = False  # tracks whether the Load button should be enabled
        uploaded_provider = None
        uploaded_portfolio = None
        uploaded_scores = None
        selected_dataset = None

        if data_source == "Sample Data":
            st.info("📁 Built-in example data will be used for demonstration.")
            _ready_to_load = True

        elif data_source == "Upload Custom Data":
            if is_cloud:
                st.warning(
                    "⚠️ **Cloud deployment detected.** Any data you upload will be "
                    "processed on Streamlit's servers (US-based). For sensitive or "
                    "confidential portfolio data, use the local Docker installation instead."
                )
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
            
            if uploaded_provider is not None and uploaded_portfolio is not None:
                _ready_to_load = True
            else:
                st.warning("⚠️ Please upload both files to continue")

        elif data_source == "Pre-scored Data (4b format)":
            if is_cloud:
                st.warning(
                    "⚠️ **Cloud deployment detected.** Any data you upload will be "
                    "processed on Streamlit's servers (US-based). For sensitive or "
                    "confidential portfolio data, use the local Docker installation instead."
                )
            st.info(
                "Upload an Excel file containing pre-computed temperature scores from a "
                "data provider (the format used in notebook 4b).  "
                "Required columns: `company_id`, `company_name`, `investment_value`, "
                "`scope`, `time_frame`, `temperature_score`."
            )
            uploaded_scores = st.file_uploader(
                "Pre-scored portfolio (Excel)",
                type=["xlsx", "xls"],
                key="scores_file",
                help="Excel file with one row per company/scope/timeframe combination",
            )
            if uploaded_scores is not None:
                _ready_to_load = True
            else:
                st.warning("⚠️ Please upload the pre-scored Excel file to continue")

        else:  # Load from Database
            init_db()
            datasets = get_saved_datasets()
            if not datasets:
                st.warning("No saved datasets found. Load data from files first and save it.")
            else:
                dataset_names = [d["name"] for d in datasets]
                selected_dataset = st.selectbox(
                    "Select Dataset",
                    options=dataset_names,
                    help="Choose a previously saved dataset"
                )
                
                # Show dataset info
                ds_info = next(d for d in datasets if d["name"] == selected_dataset)
                st.caption(f"Updated: {ds_info['updated_at'][:16]}")
                if ds_info.get("description"):
                    st.caption(ds_info["description"])
                
                # Delete button
                if st.button("🗑️ Delete this dataset", key="delete_ds"):
                    delete_saved_dataset(selected_dataset)
                    st.success(f"Deleted '{selected_dataset}'")
                    st.rerun()
                
                _ready_to_load = True

        # -- Load Data button --------------------------------------------------
        st.divider()
        data_is_loaded = st.session_state.get("data_loaded", False)

        if data_is_loaded:
            st.success(f"✅ Data loaded ({st.session_state.get('_loaded_source', data_source)})")
            if st.button("🔄 Reload / Change Source", key="reload_data"):
                for _key in ("data_loaded", "portfolio_df", "fundamental_df", "target_df",
                             "scoring_results", "calculation_run",
                             "edit_portfolio_mode", "edit_fundamental_mode", "edit_target_mode",
                             "provider_scores_df", "data_mode", "ps_aggregation_result"):
                    st.session_state.pop(_key, None)
                st.rerun()
        else:
            load_clicked = st.button(
                "📥 Load Data",
                type="primary",
                disabled=not _ready_to_load,
                key="load_data_btn",
                help="Click to load the selected data source",
                use_container_width=True,
            )

            if load_clicked:
                try:
                    if data_source == "Sample Data":
                        provider_path, portfolio_path = download_sample_data()
                        provider = load_provider_data(provider_path)
                        portfolio_df = load_portfolio_data(portfolio_path)
                        provider_dfs = extract_provider_dataframes(provider_path)
                        fundamental_df = provider_dfs["fundamental_data"]
                        target_df = provider_dfs["target_data"]

                    elif data_source == "Upload Custom Data":
                        provider_path = load_uploaded_provider_file(uploaded_provider)
                        provider = load_provider_data(provider_path)
                        portfolio_df = load_uploaded_portfolio_file(uploaded_portfolio)
                        provider_dfs = extract_provider_dataframes(provider_path)
                        fundamental_df = provider_dfs["fundamental_data"]
                        target_df = provider_dfs["target_data"]
                        # Validate portfolio
                        is_valid, missing = validate_portfolio_data(portfolio_df)
                        if not is_valid:
                            st.error(f"❌ Missing required columns: {', '.join(missing)}")
                            st.stop()

                    elif data_source == "Pre-scored Data (4b format)":
                        df_raw = load_uploaded_provider_scores_file(uploaded_scores)
                        is_valid, missing = validate_provider_scores_data(df_raw)
                        if not is_valid:
                            st.error(
                                f"❌ Missing required columns in pre-scored file: {', '.join(missing)}"
                            )
                            st.stop()
                        provider_scores_df = prepare_provider_scores_df(df_raw)
                        st.session_state.provider_scores_df = provider_scores_df
                        st.session_state.data_mode = "provider_scores"
                        # Placeholders so non-branched code downstream doesn't KeyError
                        portfolio_df = pd.DataFrame()
                        fundamental_df = pd.DataFrame()
                        target_df = pd.DataFrame()

                    else:  # Load from Database
                        db_data = load_data_from_db(selected_dataset)
                        portfolio_df = db_data["portfolio"]
                        fundamental_df = db_data["fundamental_data"]
                        target_df = db_data["target_data"]

                    # Persist loaded data into session state
                    st.session_state.portfolio_df = portfolio_df.copy()
                    st.session_state.fundamental_df = fundamental_df.copy()
                    st.session_state.target_df = target_df.copy()
                    st.session_state._data_source = data_source
                    st.session_state._loaded_source = data_source
                    st.session_state.data_loaded = True
                    # Clear stale scoring results
                    st.session_state.pop("scoring_results", None)
                    st.session_state.pop("coverage_result", None)
                    st.session_state.pop("_committed_key", None)
                    st.session_state.pop("calculation_run", None)
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Failed to load data: {e}")
                    logger.exception("Data loading failed")

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

        # --- SBTi & Coverage Settings ---
        if st.session_state.get("data_mode") != "provider_scores":
            st.markdown("#### SBTi Settings")

            sbti_factor = st.number_input(
                "SBTi Factor",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.05,
                help=(
                    "Blending factor for companies without SBTi-validated targets. "
                    "1.0 = all scores calculated from targets regardless of SBTi status. "
                    "Values < 1 blend toward the default score for non-validated companies."
                ),
            )

            calculate_coverage = st.checkbox(
                "Calculate portfolio coverage",
                value=False,
                help="Run SBTi portfolio coverage analysis (requires CTA file when enabled)",
            )

            # Only show CTA / offline controls when a CTA file is actually needed
            _needs_cta = sbti_factor != 1.0 or calculate_coverage
            st.session_state["_prev_needs_cta"] = st.session_state.get("_needs_cta_last", False)
            st.session_state["_needs_cta_last"] = _needs_cta
            cta_file_path = None  # default: auto-download (or not needed)

            if _needs_cta:
                st.markdown("#### CTA File")
                cta_source = st.radio(
                    "Companies Taking Action data",
                    options=["Auto-download from SBTi", "Upload custom file"],
                    index=0,
                    help="The CTA file lists companies with validated SBTi targets",
                )

                if cta_source == "Upload custom file":
                    cta_upload = st.file_uploader(
                        "Upload CTA Excel file",
                        type=["xlsx", "xls"],
                        key="cta_file",
                    )
                    if cta_upload is not None:
                        import tempfile as _tmpmod
                        _cta_tmp = _tmpmod.NamedTemporaryFile(delete=False, suffix=".xlsx")
                        _cta_tmp.write(cta_upload.getvalue())
                        _cta_tmp.close()
                        cta_file_path = _cta_tmp.name
                    else:
                        st.warning("⚠️ Please upload a CTA file or switch to auto-download")

                offline_mode = st.checkbox(
                    "Offline mode",
                    value=False,
                    help=(
                        "When enabled, uses a cached/bundled CTA file instead of "
                        "downloading from SBTi. Useful behind firewalls."
                    ),
                )
                PortfolioCoverageTVPConfig.OFFLINE = offline_mode
                import os as _os
                if offline_mode:
                    _os.environ["ITR_OFFLINE"] = "1"
                else:
                    _os.environ.pop("ITR_OFFLINE", None)
            else:
                # Reset offline state when CTA is not needed
                PortfolioCoverageTVPConfig.OFFLINE = False
                import os as _os
                _os.environ.pop("ITR_OFFLINE", None)
        else:
            # Pre-scored mode — SBTi settings not applicable
            sbti_factor = 1.0
            calculate_coverage = False
            cta_file_path = None
            PortfolioCoverageTVPConfig.OFFLINE = False
            import os as _os
            _os.environ.pop("ITR_OFFLINE", None)
    
    # ------------------------------------------------------------------
    # Guard: show landing page if no data loaded yet
    # ------------------------------------------------------------------
    if not st.session_state.get("data_loaded", False):
        st.markdown("---")
        st.markdown(
            """
            ### 👋 Welcome! Choose a data source to get started.

            Use the **sidebar** on the left to:
            1. **Select** a data source (Sample Data, Upload, or Database)
            2. Configure any required options (e.g. upload files)
            3. Click **📥 Load Data** to begin

            Once data is loaded you'll be able to review, edit, and run temperature
            scoring analysis on your portfolio.
            """
        )
        st.stop()

    # Determine data mode — set at load time for pre-scored uploads
    is_provider_scores_mode = st.session_state.get("data_mode") == "provider_scores"

    # ------------------------------------------------------------------
    # Data Review & Editing Section  —  or pre-scored preview
    # ------------------------------------------------------------------
    if is_provider_scores_mode:
        # ---- Pre-scored mode: read-only preview + aggregation ----
        amended_portfolio = st.session_state.provider_scores_df
        portfolio_df = amended_portfolio
        fundamental_df = amended_portfolio

        st.markdown("---")
        st.subheader("📊 Pre-scored Portfolio Data")

        _ps_unique = amended_portfolio["company_id"].nunique() if "company_id" in amended_portfolio.columns else "N/A"
        _ps_scopes = sorted({str(s.name) for s in amended_portfolio["scope"].unique()}) if "scope" in amended_portfolio.columns else []
        _ps_tfs = sorted({str(t.name) for t in amended_portfolio["time_frame"].unique()}) if "time_frame" in amended_portfolio.columns else []
        _ps_c1, _ps_c2, _ps_c3 = st.columns(3)
        _ps_c1.metric("Rows", len(amended_portfolio))
        _ps_c2.metric("Companies", _ps_unique)
        _ps_c3.metric("Scopes", ", ".join(_ps_scopes) or "N/A")
        st.caption(f"Time frames present: {', '.join(_ps_tfs) or 'N/A'}")

        with st.expander("🔍 Preview data", expanded=False):
            _preview_df = amended_portfolio.head(40).copy()
            for _col in ("scope", "time_frame"):
                if _col in _preview_df.columns:
                    _preview_df[_col] = _preview_df[_col].apply(
                        lambda x: x.name if hasattr(x, "name") else str(x)
                    )
            st.dataframe(_preview_df, use_container_width=True)

        # Aggregate scores — cached per (data hash + analysis params)
        def _df_hash(df: pd.DataFrame) -> str:
            return hashlib.md5(
                pd.util.hash_pandas_object(df, index=True).values.tobytes()
            ).hexdigest()

        _ps_key = (
            _df_hash(amended_portfolio),
            tuple(tf.value for tf in time_frames),
            tuple(sc.value for sc in scopes),
            aggregation_method.value if hasattr(aggregation_method, "value") else str(aggregation_method),
        )
        _ps_cached = st.session_state.get("ps_aggregation_result")
        if _ps_cached is not None and _ps_cached.get("key") == _ps_key:
            aggregated_scores = _ps_cached["aggregated_scores"]
        else:
            with st.spinner("Aggregating scores..."):
                aggregated_scores = aggregate_portfolio_scores(
                    amended_portfolio=amended_portfolio,
                    time_frames=time_frames,
                    scopes=scopes,
                    aggregation_method=aggregation_method,
                )
            st.session_state.ps_aggregation_result = {
                "key": _ps_key,
                "aggregated_scores": aggregated_scores,
            }
        coverage = None

    else:
        # ---- Normal scoring mode: review, edit, run analysis ----

        st.markdown("---")
        st.subheader("📝 Review & Edit Data")
        st.caption(
            "Inspect the loaded data below. Click **Edit** to modify a table. "
            "Use **Save to Database** to persist changes between sessions."
        )

        # Toggle flags for editing mode
        for _flag in ("edit_portfolio_mode", "edit_fundamental_mode", "edit_target_mode"):
            if _flag not in st.session_state:
                st.session_state[_flag] = False

        edit_tab1, edit_tab2, edit_tab3 = st.tabs([
            "Portfolio", "Company Fundamentals", "Targets"
        ])

        with edit_tab1:
            st.markdown(f"**{len(st.session_state.portfolio_df)} companies** in portfolio")
            if st.session_state.get("portfolio_dropped_warning"):
                st.warning(st.session_state.pop("portfolio_dropped_warning"))
            if st.session_state.edit_portfolio_mode:
                edited_portfolio = st.data_editor(
                    st.session_state.portfolio_df,
                    num_rows="dynamic",
                    width="stretch",
                    key="edit_portfolio",
                )
                col_apply, col_cancel = st.columns(2)
                with col_apply:
                    if st.button("✅ Apply changes", key="apply_portfolio"):
                        _cleaned, _dropped = clean_portfolio_df(edited_portfolio)
                        if _dropped > 0:
                            st.session_state["portfolio_dropped_warning"] = (
                                f"Removed {_dropped} incomplete row(s) (missing company_id, company_name, or valid investment_value)."
                            )
                        st.session_state.portfolio_df = _cleaned
                        st.session_state.edit_portfolio_mode = False
                        st.session_state.pop("scoring_results", None)
                        st.session_state.pop("coverage_result", None)
                        st.session_state.pop("_committed_key", None)
                        st.rerun()
                with col_cancel:
                    if st.button("Cancel", key="cancel_portfolio"):
                        st.session_state.edit_portfolio_mode = False
                        st.rerun()
            else:
                st.dataframe(st.session_state.portfolio_df, width="stretch", height=400)
                if st.button("✏️ Edit Portfolio", key="toggle_edit_portfolio"):
                    st.session_state.edit_portfolio_mode = True
                    st.rerun()

        with edit_tab2:
            st.markdown(f"**{len(st.session_state.fundamental_df)} companies** with fundamental data")
            if st.session_state.get("fundamental_dropped_warning"):
                st.warning(st.session_state.pop("fundamental_dropped_warning"))
            if st.session_state.edit_fundamental_mode:
                edited_fundamental = st.data_editor(
                    st.session_state.fundamental_df,
                    num_rows="dynamic",
                    width="stretch",
                    key="edit_fundamental",
                )
                col_apply, col_cancel = st.columns(2)
                with col_apply:
                    if st.button("✅ Apply changes", key="apply_fundamental"):
                        _cleaned, _dropped = clean_fundamental_df(edited_fundamental)
                        if _dropped > 0:
                            st.session_state["fundamental_dropped_warning"] = (
                                f"Removed {_dropped} invalid row(s) (missing company_id or company_name)."
                            )
                        st.session_state.fundamental_df = _cleaned
                        st.session_state.edit_fundamental_mode = False
                        st.session_state.pop("scoring_results", None)
                        st.session_state.pop("coverage_result", None)
                        st.session_state.pop("_committed_key", None)
                        st.rerun()
                with col_cancel:
                    if st.button("Cancel", key="cancel_fundamental"):
                        st.session_state.edit_fundamental_mode = False
                        st.rerun()
            else:
                st.dataframe(st.session_state.fundamental_df, width="stretch", height=400)
                if st.button("✏️ Edit Fundamentals", key="toggle_edit_fundamental"):
                    st.session_state.edit_fundamental_mode = True
                    st.rerun()

        with edit_tab3:
            st.markdown(f"**{len(st.session_state.target_df)} targets**")
            if st.session_state.get("target_dropped_warning"):
                st.warning(st.session_state.pop("target_dropped_warning"))
            if st.session_state.edit_target_mode:
                edited_target = st.data_editor(
                    st.session_state.target_df,
                    num_rows="dynamic",
                    width="stretch",
                    key="edit_target",
                )
                col_apply, col_cancel = st.columns(2)
                with col_apply:
                    if st.button("✅ Apply changes", key="apply_target"):
                        _cleaned, _dropped = clean_target_df(edited_target)
                        if _dropped > 0:
                            st.session_state["target_dropped_warning"] = (
                                f"Removed {_dropped} invalid row(s) (missing company_id, target_type, scope, base_year, or end_year)."
                            )
                        st.session_state.target_df = _cleaned
                        st.session_state.edit_target_mode = False
                        st.session_state.pop("scoring_results", None)
                        st.session_state.pop("coverage_result", None)
                        st.session_state.pop("_committed_key", None)
                        st.rerun()
                with col_cancel:
                    if st.button("Cancel", key="cancel_target"):
                        st.session_state.edit_target_mode = False
                        st.rerun()
            else:
                st.dataframe(st.session_state.target_df, width="stretch", height=400)
                if st.button("✏️ Edit Targets", key="toggle_edit_target"):
                    st.session_state.edit_target_mode = True
                    st.rerun()

        # Use the (possibly edited) session-state versions going forward
        # Clean all DataFrames so the UI always shows exactly what the calculation uses
        portfolio_df, _ = clean_portfolio_df(st.session_state.portfolio_df)
        st.session_state.portfolio_df = portfolio_df

        fundamental_df, _ = clean_fundamental_df(st.session_state.fundamental_df)
        st.session_state.fundamental_df = fundamental_df

        target_df, _ = clean_target_df(st.session_state.target_df)
        st.session_state.target_df = target_df

        # -- Save to Database (uses edited data) --------------------------------
        with st.expander("💾 Save data to local database", expanded=False):
            save_col1, save_col2 = st.columns([2, 1])
            with save_col1:
                save_name = st.text_input(
                    "Dataset name",
                    value="my_dataset",
                    key="save_ds_name",
                    help="Give this dataset a name for later retrieval"
                )
                save_desc = st.text_input(
                    "Description (optional)",
                    value="",
                    key="save_ds_desc",
                )
            with save_col2:
                st.markdown("")
                st.markdown("")
                if st.button("💾 Save", type="primary", key="save_to_db"):
                    save_data_to_db(save_name, portfolio_df, fundamental_df, target_df, save_desc)
                    st.success(f"✅ Saved as '{save_name}'")

        # Rebuild provider from current (possibly edited) DataFrames
        provider = create_provider_from_dataframes(fundamental_df, target_df)

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
            st.info(f"**Source:** {st.session_state.get('_loaded_source', data_source)}")
        with col2:
            st.markdown("")
        with col3:
            if 'calculation_run' not in st.session_state:
                st.session_state.calculation_run = False

            if st.button("▶️ Run Analysis", type="primary", width="stretch"):
                st.session_state.calculation_run = True
                st.session_state["_committed_key"] = None  # force recalculation

            if st.session_state.calculation_run:
                if st.button("🔄 Reset", width="stretch"):
                    st.session_state.calculation_run = False
                    st.session_state.pop("scoring_results", None)
                    st.session_state.pop("coverage_result", None)
                    st.session_state.pop("_committed_key", None)
                    st.rerun()

        if not st.session_state.calculation_run:
            st.warning("⏳ Click **Run Analysis** to calculate temperature scores")
            st.stop()

        st.markdown("---")

        # ------------------------------------------------------------------
        # Two-level cache:
        #   _score_key  — covers temperature scores + aggregation (slow).
        #                 Does NOT include calculate_coverage so toggling the
        #                 coverage checkbox never forces a full rescore.
        #   _full_key   — used for the "params changed" guard and the fast
        #                 coverage cache, so coverage is re-run when its own
        #                 inputs (aggregation method, cta path, checkbox) change.
        # ------------------------------------------------------------------
        def _df_hash(df: pd.DataFrame) -> str:
            return hashlib.md5(
                pd.util.hash_pandas_object(df, index=True).values.tobytes()
            ).hexdigest()

        _data_hash = _df_hash(portfolio_df) + _df_hash(fundamental_df) + _df_hash(target_df)

        _score_key = (
            _data_hash,
            tuple(tf.value for tf in time_frames),
            tuple(sc.value for sc in scopes),
            aggregation_method.value if hasattr(aggregation_method, 'value') else str(aggregation_method),
            sbti_factor,
            cta_file_path,
        )
        _full_key = (_score_key, calculate_coverage)

        # If parameters changed since the last committed run, pause and prompt the
        # user to click Run Analysis again — prevents immediate recalculation on
        # every sidebar interaction (e.g. clicking sbti_factor +/- multiple times).
        # Only _score_key is used here — toggling coverage alone does not require
        # a full rerun since coverage is calculated independently.
        _committed_key = st.session_state.get("_committed_key")
        if _committed_key is not None and _committed_key != _score_key:
            st.session_state.calculation_run = False
            st.warning("⚙️ Parameters changed — click **▶️ Run Analysis** to recalculate")
            st.stop()

        # --- Temperature scores + aggregation (expensive) ---
        _score_cached = st.session_state.get("scoring_results")
        if _score_cached is not None and _score_cached.get("key") == _score_key:
            amended_portfolio = _score_cached["amended_portfolio"]
            aggregated_scores = _score_cached["aggregated_scores"]
        else:
            with st.spinner("Calculating temperature scores..."):
                amended_portfolio = calculate_temperature_scores(
                    _provider=provider,
                    _companies=companies,
                    time_frames=time_frames,
                    scopes=scopes,
                    aggregation_method=aggregation_method,
                    sbti_factor=sbti_factor,
                    cta_file_path=cta_file_path,
                    data_hash=_data_hash,
                )
                aggregated_scores = aggregate_portfolio_scores(
                    amended_portfolio=amended_portfolio,
                    time_frames=time_frames,
                    scopes=scopes,
                    aggregation_method=aggregation_method,
                    sbti_factor=sbti_factor,
                )
            st.session_state.scoring_results = {
                "key": _score_key,
                "amended_portfolio": amended_portfolio,
                "aggregated_scores": aggregated_scores,
            }

        # --- Portfolio coverage (fast, separate cache) ---
        _cov_cached = st.session_state.get("coverage_result")
        if calculate_coverage:
            if _cov_cached is not None and _cov_cached.get("key") == _full_key:
                coverage = _cov_cached["coverage"]
            else:
                with st.spinner("Calculating portfolio coverage..."):
                    coverage = calculate_portfolio_coverage(
                        amended_portfolio, aggregation_method,
                        cta_file_path=cta_file_path,
                    )
                st.session_state.coverage_result = {"key": _full_key, "coverage": coverage}
        else:
            coverage = None

        st.session_state["_committed_key"] = _score_key

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
            if coverage is not None:
                st.metric("Portfolio Coverage", f"{coverage:.1f}%")
            else:
                st.metric("Portfolio Coverage", "N/A")
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
            plot_portfolio_summary_metrics(portfolio_score, coverage if coverage is not None else 0),
            width="stretch"
        )

        # Score matrix
        st.subheader("Temperature Scores by Timeframe & Scope")
        scores_df = get_aggregated_scores_df(aggregated_scores)
        st.dataframe(scores_df, width="stretch")

        # Portfolio data preview
        with st.expander("📋 View Portfolio Data"):
            _pf_display = portfolio_df.head(20).copy()
            for _col in ("scope", "time_frame"):
                if _col in _pf_display.columns:
                    _pf_display[_col] = _pf_display[_col].apply(
                        lambda x: x.name if hasattr(x, "name") else str(x)
                    )
            st.dataframe(_pf_display, width="stretch")

    # Tab 2: Hotspot Analysis
    with tab2:
        st.header("Hotspot Analysis")

        # Available parameters: only those columns that exist and have data
        _HS_PARAMS = {
            "Region":    "region",
            "Country":   "country",
            "Sector":    "sector",
            "Industry":  "industry_level_1",
            "Scope":     "scope",
            "Timeframe": "time_frame",
        }
        available_params = [
            name for name, col in _HS_PARAMS.items()
            if col in amended_portfolio.columns
            and amended_portfolio[col].notna().any()
        ]

        def _hs_to_str(v):
            return v.name if hasattr(v, "name") else str(v)

        def _hs_unique_vals(col: str) -> list:
            raw = amended_portfolio[col].dropna().unique().tolist()
            return sorted({_hs_to_str(v) for v in raw})

        if len(available_params) < 1:
            st.warning("No groupable columns found in the loaded data.")
        else:
            # ---- Filters ------------------------------------------------
            st.subheader("Filters")
            f_col1, f_col2 = st.columns(2)

            with f_col1:
                filter1_param = st.selectbox(
                    "Filter 1 — parameter", ["None"] + available_params, key="hs_f1_param"
                )
                if filter1_param != "None":
                    filter1_val = st.selectbox(
                        filter1_param,
                        _hs_unique_vals(_HS_PARAMS[filter1_param]),
                        key="hs_f1_val",
                    )
                else:
                    filter1_val = None

            remaining_params = [p for p in available_params if p != filter1_param]

            with f_col2:
                filter2_param = st.selectbox(
                    "Filter 2 — parameter", ["None"] + remaining_params, key="hs_f2_param"
                )
                if filter2_param != "None":
                    filter2_val = st.selectbox(
                        filter2_param,
                        _hs_unique_vals(_HS_PARAMS[filter2_param]),
                        key="hs_f2_val",
                    )
                else:
                    filter2_val = None

            # ---- Apply filters on a string-converted copy ---------------
            _df = amended_portfolio.copy()
            for _hscol in _HS_PARAMS.values():
                if _hscol in _df.columns:
                    _df[_hscol] = _df[_hscol].apply(_hs_to_str)

            if filter1_val is not None:
                _df = _df[_df[_HS_PARAMS[filter1_param]] == filter1_val]
            if filter2_val is not None:
                _df = _df[_df[_HS_PARAMS[filter2_param]] == filter2_val]

            # ---- Axis selection -----------------------------------------
            used_as_filter = {filter1_param, filter2_param} - {"None"}
            axis_params = [p for p in available_params if p not in used_as_filter]

            st.subheader("Chart Axes")
            ax_col1, ax_col2 = st.columns(2)

            with ax_col1:
                x_param = (
                    st.selectbox("X-axis", axis_params, key="hs_x")
                    if axis_params else None
                )
            y_options = ["None"] + [p for p in axis_params if p != x_param]
            with ax_col2:
                y_param = (
                    st.selectbox(
                        "Y-axis (optional — adds heatmap dimension)", y_options, key="hs_y"
                    )
                    if len(y_options) > 1 else None
                )

            # ---- Build chart --------------------------------------------
            if not _df.empty and x_param:
                x_col = _HS_PARAMS[x_param]
                _df["_num"] = _df["temperature_score"] * _df["investment_value"]

                # Build filter description for headings
                _active_filters = []
                if filter1_val is not None:
                    _active_filters.append(f"{filter1_param} = {filter1_val}")
                if filter2_val is not None:
                    _active_filters.append(f"{filter2_param} = {filter2_val}")
                _filter_suffix = f" — filtered by {', '.join(_active_filters)}" if _active_filters else ""
                _subtitle = f"<br><sup>Aggregation: {selected_agg}</sup>"

                if y_param and y_param != "None":
                    y_col = _HS_PARAMS[y_param]
                    _sum_num = _df.groupby([y_col, x_col])["_num"].sum()
                    _sum_wt  = _df.groupby([y_col, x_col])["investment_value"].sum()
                    _cell_scores = (
                        _sum_num / _sum_wt.replace(0, float("nan"))
                    ).rename("score")
                    pivot = _cell_scores.unstack(level=x_col)

                    fig = plot_heatmap(
                        pivot=pivot,
                        x_label=x_param,
                        y_label=y_param,
                        title=f"Temperature Scores by {y_param} / {x_param}{_filter_suffix}{_subtitle}",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    _sum_num = _df.groupby(x_col)["_num"].sum()
                    _sum_wt  = _df.groupby(x_col)["investment_value"].sum()
                    _cell_scores = (
                        _sum_num / _sum_wt.replace(0, float("nan"))
                    ).reset_index()
                    _cell_scores.columns = [x_param, "Temperature Score (°C)"]
                    _cell_scores = _cell_scores.sort_values(
                        "Temperature Score (°C)", ascending=False
                    )

                    fig = px.bar(
                        _cell_scores,
                        x=x_param,
                        y="Temperature Score (°C)",
                        color="Temperature Score (°C)",
                        color_continuous_scale="RdYlGn_r",
                        range_color=[1.5, 3.4],
                        title=f"Temperature Scores by {x_param}{_filter_suffix}{_subtitle}",
                        text=_cell_scores["Temperature Score (°C)"].round(2),
                    )
                    fig.update_traces(textposition="outside")
                    fig.update_layout(
                        yaxis=dict(range=[0, 4.0]),
                        xaxis_title=x_param,
                    )
                    fig.add_hline(
                        y=2.0, line_dash="dash", line_color="orange", annotation_text="2.0°C"
                    )
                    fig.add_hline(
                        y=1.5, line_dash="dash", line_color="green", annotation_text="1.5°C"
                    )
                    st.plotly_chart(fig, use_container_width=True)

            elif _df.empty:
                st.warning("No data matches the selected filters.")
            else:
                st.info("Select an X-axis parameter above to display the chart.")

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
        st.plotly_chart(contrib_fig, width="stretch")

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
            width="stretch",
            height=400
        )

    # Tab 4: What-If Scenarios
    with tab4:
        if is_provider_scores_mode:
            st.info(
                "ℹ️ **Scenario analysis is not available for pre-scored data.** "
                "This feature requires the full ITR scoring pipeline. "
                "To run scenario analysis, use **Sample Data** or **Upload Custom Data** as your data source."
            )
        else:
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
                    # Build display labels with impact score, sorted by descending impact
                    candidates = candidates.sort_values('impact_score', ascending=False)
                    total_impact = candidates['impact_score'].sum()
                    candidates['impact_pct'] = (
                        (candidates['impact_score'] / total_impact * 100) if total_impact > 0 else 0
                    ).round(1)
                    candidates['display_label'] = (
                        candidates['company_name'] + '  (' + candidates['impact_pct'].astype(str) + '% impact)'
                    )

                    # Multi-select for companies
                    company_options = candidates['display_label'].tolist()
                    selected_labels = st.multiselect(
                        "Select Companies to Engage",
                        options=company_options,
                        default=company_options[:3] if len(company_options) >= 3 else company_options,
                        help="Companies sorted by descending impact on portfolio score"
                    )

                    # Get company IDs for selected labels
                    engagement_ids = candidates[
                        candidates['display_label'].isin(selected_labels)
                    ]['company_id'].tolist()

                    st.dataframe(
                        candidates[candidates['display_label'].isin(selected_labels)].drop(
                            columns=['display_label', 'impact_pct']
                        ),
                        width="stretch",
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
                        sbti_factor=sbti_factor,
                        cta_file_path=cta_file_path,
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
