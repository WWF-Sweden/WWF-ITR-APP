"""Release analysis data owned by the current Streamlit session."""
from utils.cta import store_cta_upload


def clear_loaded_data(state):
    """Reset loaded data and uploads; leave explicitly saved datasets intact.

    Call before creating upload widgets, or as a Streamlit button callback.
    This releases references; it does not securely erase process memory.
    """
    store_cta_upload(state, None)
    for key in (
        "data_loaded", "portfolio_df", "fundamental_df", "target_df",
        "scoring_results", "coverage_result", "_scenario_cache", "_committed_key", "calculation_run",
        "edit_portfolio_mode", "edit_fundamental_mode", "edit_target_mode",
        "provider_scores_df", "data_mode", "ps_aggregation_result", "_loaded_source",
        "portfolio_dropped_warning", "fundamental_dropped_warning", "target_dropped_warning",
        "provider_file", "portfolio_file", "scores_file", "cta_file",
        "_cta_upload_path", "_cta_upload_digest", "_cta_upload_directory",
    ):
        state.pop(key, None)
