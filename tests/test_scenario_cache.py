"""Scenario caching must save work without sharing or confusing input data."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
from ITR.interfaces import EScope, ETimeFrames
from ITR.temperature_score import ScenarioType, EngagementType
from ITR.portfolio_aggregation import PortfolioAggregationMethod
from utils import scenarios
from utils.session import clear_loaded_data


class ScenarioCacheTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.kwargs = dict(
            _provider=SimpleNamespace(data={
                "fundamental_data": pd.DataFrame({"company_id": ["example"], "ghg_s1": [100.0]}),
                "target_data": pd.DataFrame({"company_id": ["example"], "reduction_ambition": [0.5]}),
            }),
            portfolio_df=pd.DataFrame({"company_id": ["example"], "investment_value": [100.0]}),
            engagement_company_ids=["example"], scenario_type=ScenarioType.TARGETS,
            engagement_type=EngagementType.SET_TARGETS, time_frames=[ETimeFrames.MID],
            scopes=[EScope.S1S2], aggregation_method=PortfolioAggregationMethod.WATS,
        )
        self.result = (pd.DataFrame({"temperature_score": [2.0]}), {"score": 2.0})
        self.mock = patch.object(scenarios, "_calculate_scenario_analysis", return_value=self.result)
        self.calculate = self.mock.start()
        self.addCleanup(self.mock.stop)

    def run_scenario(self, state=None, **changes):
        return scenarios.run_scenario_analysis(
            session_state=self.state if state is None else state,
            **(self.kwargs | changes),
        )

    def test_identical_inputs_reuse_result_but_other_sessions_do_not(self):
        self.run_scenario()
        self.run_scenario(**copy.deepcopy(self.kwargs))
        self.assertEqual(self.calculate.call_count, 1)
        self.run_scenario(state={})
        self.assertEqual(self.calculate.call_count, 2)

    def test_changed_provider_values_schema_and_portfolio_invalidate(self):
        self.run_scenario()
        provider = self.kwargs["_provider"]
        provider.data["target_data"].loc[0, "reduction_ambition"] = 0.6
        self.run_scenario()
        provider.data["fundamental_data"].loc[0, "ghg_s1"] = 200
        self.run_scenario()
        provider.data["target_data"].rename(columns={"reduction_ambition": "other"}, inplace=True)
        self.run_scenario()
        self.kwargs["portfolio_df"].loc[0, "investment_value"] = 200
        self.run_scenario()
        self.assertEqual(self.calculate.call_count, 5)

    def test_analysis_options_are_part_of_key(self):
        self.run_scenario()
        changes = [
            {"engagement_company_ids": []}, {"scenario_type": ScenarioType.APPROVED_TARGETS},
            {"engagement_type": EngagementType.SET_SBTI_TARGETS},
            {"time_frames": [ETimeFrames.LONG]}, {"scopes": [EScope.S3]},
            {"aggregation_method": PortfolioAggregationMethod.TETS}, {"grouping": ["sector"]},
        ]
        # Isolate option invalidation from eviction of the small cache.
        for change in changes:
            self.state.clear()
            self.run_scenario()
            before = self.calculate.call_count
            self.run_scenario(**change)
            self.assertEqual(self.calculate.call_count, before + 1)

    def test_provider_column_mapping_is_part_of_key(self):
        self.kwargs["_provider"].c = SimpleNamespace(COMPANY_ID="company_id")
        self.run_scenario()
        self.kwargs["_provider"].c.COMPANY_ID = "other_id"
        self.run_scenario()
        self.assertEqual(self.calculate.call_count, 2)

    def test_cta_contents_are_checked_even_if_supplied_hash_is_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cta.xlsx"
            path.write_bytes(b"first snapshot")
            args = dict(cta_file_path=str(path), sbti_factor=0.8, cta_hash="same")
            self.run_scenario(**args)
            self.run_scenario(**args)
            self.assertEqual(self.calculate.call_count, 1)
            path.write_bytes(b"second snapshot")
            self.run_scenario(**args)
            self.run_scenario(**(args | {"sbti_factor": 0.5}))
            self.assertEqual(self.calculate.call_count, 3)

    def test_unfingerprinted_default_cta_is_not_cached(self):
        self.run_scenario(sbti_factor=0.8)
        self.run_scenario(sbti_factor=0.8)
        self.assertEqual(self.calculate.call_count, 2)
        self.assertNotIn("_scenario_cache", self.state)

    def test_cached_result_cannot_be_changed_by_caller(self):
        first, aggregation = self.run_scenario()
        first.loc[0, "temperature_score"] = 99
        aggregation["score"] = 99
        second, aggregation = self.run_scenario()
        self.assertEqual(second.loc[0, "temperature_score"], 2)
        self.assertEqual(aggregation["score"], 2)

    def test_three_entry_limit_evicts_least_recently_used(self):
        for value in (0, 1, 2, 0, 3, 1):
            self.run_scenario(grouping=[str(value)])
        self.assertEqual(self.calculate.call_count, 5)
        self.assertEqual(len(self.state["_scenario_cache"]), 3)

    def test_byte_budget_evicts_entries_and_skips_oversized_result(self):
        import pickle
        size = len(pickle.dumps(self.result, protocol=5))
        with patch.object(scenarios, "SCENARIO_CACHE_MAX_BYTES", size):
            self.run_scenario(grouping=["a"])
            self.run_scenario(grouping=["b"])
            self.assertEqual(len(self.state["_scenario_cache"]), 1)
        self.state.clear()
        with patch.object(scenarios, "SCENARIO_CACHE_MAX_BYTES", 1):
            self.run_scenario()
            self.run_scenario()
            self.assertEqual(len(self.state["_scenario_cache"]), 0)

    def test_errors_are_not_cached(self):
        self.calculate.side_effect = ValueError("failed calculation")
        for _ in range(2):
            with self.assertRaises(ValueError):
                self.run_scenario()
        self.assertEqual(self.calculate.call_count, 2)
        self.assertFalse(self.state["_scenario_cache"])

    def test_explicit_reset_releases_cache(self):
        self.run_scenario()
        clear_loaded_data(self.state)
        self.assertNotIn("_scenario_cache", self.state)
        self.run_scenario()
        self.assertEqual(self.calculate.call_count, 2)


if __name__ == "__main__":
    unittest.main()
