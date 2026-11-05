"""Local data lifecycle and calculation isolation regression tests."""
import gc
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from ITR.data.excel import ExcelProvider
from ITR.interfaces import ETimeFrames, EScope
from ITR.portfolio_aggregation import PortfolioAggregationMethod
from ITR.temperature_score import ScenarioType, EngagementType
from utils import data_loader, cta
from utils.scenarios import run_scenario_analysis
from utils.session import clear_loaded_data


def upload(content, name):
    stream = io.BytesIO(content)
    stream.name = name
    return stream


class LocalDataTests(unittest.TestCase):
    def test_provider_roundtrip_and_uploads_do_not_create_temporary_files(self):
        source = Path(__file__).resolve().parents[1] / "data/data_provider_example_360.xlsx"
        content = source.read_bytes()
        original = ExcelProvider(str(source))
        with patch.object(data_loader.tempfile, "NamedTemporaryFile", side_effect=AssertionError("disk copy")):
            frames = data_loader.load_uploaded_provider_file(upload(content, "provider.xlsx"))
            provider = data_loader.create_provider_from_dataframes(
                frames["fundamental_data"], frames["target_data"],
            )
            portfolio = data_loader.load_uploaded_portfolio_file(upload(
                b"company_id,company_name,investment_value\nexample,Example,100\n", "portfolio.csv",
            ))
            scores = io.BytesIO()
            pd.DataFrame({"company_id": ["example"], "temperature_score": [2.0]}).to_excel(scores, index=False)
            loaded = data_loader.load_uploaded_provider_scores_file(upload(scores.getvalue(), "scores.xlsx"))
        self.assertEqual(portfolio["investment_value"].tolist(), [100])
        self.assertEqual(loaded["temperature_score"].tolist(), [2])
        ids = original.data["fundamental_data"]["company_id"].head(3).tolist()
        self.assertEqual(original.get_targets(ids), provider.get_targets(ids))
        self.assertEqual(original.get_company_data(ids), provider.get_company_data(ids))

    def test_failed_upload_does_not_create_temporary_file(self):
        with patch.object(data_loader.tempfile, "NamedTemporaryFile", side_effect=AssertionError("disk copy")):
            with self.assertRaises(ValueError):
                data_loader.load_uploaded_provider_file(upload(b"not Excel", "broken.xlsx"))

    def test_extra_workbook_sheets_are_not_loaded(self):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for name in ("fundamental_data", "target_data", "private_notes"):
                pd.DataFrame({"value": [name]}).to_excel(writer, sheet_name=name, index=False)
        frames = data_loader.load_uploaded_provider_file(upload(buffer.getvalue(), "provider.xlsx"))
        self.assertEqual(set(frames), {"fundamental_data", "target_data"})

    def test_reset_releases_results_and_uploads_but_keeps_analysis_preferences(self):
        state = {"portfolio_df": pd.DataFrame({"company_id": ["example"]}),
                 "coverage_result": {"coverage": 100}, "_committed_key": "old",
                 "provider_file": b"upload", "scoring_results": {"score": 2},
                 "ps_aggregation_result": {"score": 2}, "sbti_factor": 0.8}
        path = cta.store_cta_upload(state, upload(b"CTA", "cta.xlsx"))
        clear_loaded_data(state)
        self.assertFalse(Path(path).exists())
        self.assertEqual(state, {"sbti_factor": 0.8})

    def test_cta_directory_is_cleaned_when_session_owner_is_released(self):
        state = {}
        path = cta.store_cta_upload(state, upload(b"CTA", "cta.xlsx"))
        self.assertTrue(Path(path).exists())
        state.clear()
        gc.collect()
        self.assertFalse(Path(path).exists())

    def test_scenario_uses_changed_provider_with_identical_portfolio_and_settings(self):
        portfolio = pd.DataFrame({"company_id": ["example"], "company_name": ["Example"],
                                  "investment_value": [100]})
        kwargs = dict(portfolio_df=portfolio, engagement_company_ids=["example"],
                      scenario_type=ScenarioType.TARGETS, engagement_type=EngagementType.SET_TARGETS,
                      time_frames=[ETimeFrames.MID], scopes=[EScope.S1S2],
                      aggregation_method=PortfolioAggregationMethod.WATS)
        with patch("utils.scenarios.TemperatureScore") as score:
            score.return_value.calculate.side_effect = [
                pd.DataFrame({"temperature_score": [2.0]}),
                pd.DataFrame({"temperature_score": [3.0]}),
            ]
            score.return_value.aggregate_scores.return_value = {"score": 2}
            first, _ = run_scenario_analysis(_provider=object(), **kwargs)
            second, _ = run_scenario_analysis(_provider=object(), **kwargs)
        self.assertEqual(first["temperature_score"].tolist(), [2])
        self.assertEqual(second["temperature_score"].tolist(), [3])


if __name__ == "__main__":
    unittest.main()
