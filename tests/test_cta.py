"""Regression tests for CTA selection and package 1.7.2 integration."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from ITR.configs import PortfolioCoverageTVPConfig as Config
from ITR.portfolio_aggregation import PortfolioAggregationMethod
from utils import cta
from utils.scoring import calculate_portfolio_coverage, calculate_temperature_scores
from ITR.interfaces import ETimeFrames, EScope


def write_cta(path, validated=True):
    pd.DataFrame({Config.COL_COMPANY_NAME: ["Example"],
                  Config.COL_COMPANY_ISIN: ["SE0000000001"],
                  Config.COL_COMPANY_LEI: [None],
                  Config.COL_TARGET: [Config.VALUE_STATUS_SET if validated else "Committed"]}).to_excel(path, index=False)


class CTATests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "cta.xlsx"
        self.path_patch = patch.object(cta, "CTA_PATH", self.path)
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.directory.cleanup()

    def test_custom_file_is_used_even_when_other_cache_exists(self):
        write_cta(self.path)
        custom = self.path.with_name("custom.xlsx")
        write_cta(custom, False)
        with patch.object(cta, "refresh_cta", side_effect=AssertionError("network")):
            selected, _ = cta.resolve_cta(custom, offline=True)
        self.assertEqual(selected, str(custom.resolve()))

    def test_offline_cached_file_never_downloads(self):
        write_cta(self.path)
        os.utime(self.path, (1, 1))
        with patch.object(cta, "refresh_cta", side_effect=AssertionError("network")):
            self.assertEqual(cta.resolve_cta(offline=True)[0], str(self.path.resolve()))

    def test_invalid_download_preserves_previous_file(self):
        write_cta(self.path)
        before = self.path.read_bytes()
        def invalid_download(instance):
            Path(instance.c.FILE_TARGETS).write_bytes(b"not Excel")
        with patch.object(cta.SBTi, "_fetch_and_save_cta_file", invalid_download):
            with self.assertRaises(cta.CTAError):
                cta.refresh_cta()
        self.assertEqual(before, self.path.read_bytes())

    def test_refresh_replaces_data_and_changes_fingerprint(self):
        write_cta(self.path)
        before = cta.cta_fingerprint(self.path)
        with patch.object(cta.SBTi, "_fetch_and_save_cta_file", lambda instance: write_cta(instance.c.FILE_TARGETS, False)):
            cta.refresh_cta()
        self.assertNotEqual(before, cta.cta_fingerprint(self.path))

    def test_upload_reuses_path_and_cleans_replaced_and_removed_files(self):
        state = {}
        upload = io.BytesIO(b"first")
        upload.name = "first.xls"
        first = cta.store_cta_upload(state, upload)
        self.assertEqual(first, cta.store_cta_upload(state, upload))
        upload = io.BytesIO(b"second")
        upload.name = "second.xlsx"
        second = cta.store_cta_upload(state, upload)
        self.assertFalse(Path(first).exists())
        self.assertTrue(Path(second).exists())
        cta.store_cta_upload(state, None)
        self.assertFalse(Path(second).exists())

    def test_invalid_file_is_an_error(self):
        pd.DataFrame({"wrong": [1]}).to_excel(self.path, index=False)
        with self.assertRaises(cta.CTAError):
            cta.resolve_cta(self.path)

    def test_temperature_config_is_restored_after_error(self):
        before = dict(vars(Config))
        with self.assertRaises(RuntimeError):
            with cta.temperature_cta_context(self.path):
                self.assertEqual(Config.FILE_TARGETS, str(self.path))
                raise RuntimeError("failed calculation")
        self.assertEqual(before, dict(vars(Config)))

    def test_temperature_cache_changes_with_cta_contents_at_same_path(self):
        calculate_temperature_scores.clear()
        write_cta(self.path)
        kwargs = dict(_provider=None, _companies=[], time_frames=[ETimeFrames.MID],
                      scopes=[EScope.S1S2], aggregation_method=PortfolioAggregationMethod.WATS,
                      sbti_factor=0.8, cta_file_path=str(self.path), data_hash="cache-test",
                      cta_hash=cta.cta_fingerprint(self.path))
        with patch("utils.scoring.TemperatureScore") as score:
            score.return_value.calculate.return_value = pd.DataFrame({"score": [2.0]})
            calculate_temperature_scores(**kwargs)
            calculate_temperature_scores(**kwargs)
            self.assertEqual(score.return_value.calculate.call_count, 1)
            write_cta(self.path, False)
            kwargs["cta_hash"] = cta.cta_fingerprint(self.path)
            calculate_temperature_scores(**kwargs)
            self.assertEqual(score.return_value.calculate.call_count, 2)
        calculate_temperature_scores.clear()

    def test_failed_auto_download_warns_and_uses_existing_file(self):
        write_cta(self.path)
        os.utime(self.path, (1, 1))
        with patch.object(cta, "refresh_cta", side_effect=cta.CTAError("network unavailable")):
            selected, warning = cta.resolve_cta()
        self.assertEqual(selected, str(self.path.resolve()))
        self.assertIn("network unavailable", warning)

    def test_offline_first_run_uses_bundled_data(self):
        with patch.object(cta, "refresh_cta", side_effect=AssertionError("network")):
            selected, warning = cta.resolve_cta(offline=True)
        self.assertTrue(Path(selected).exists())
        self.assertIn("bundled", warning)

    def test_coverage_uses_uploaded_cta_with_real_library(self):
        frame = pd.DataFrame({"company_id": ["example"], "company_name": ["Example"],
                              "company_isin": ["SE0000000001"], "company_lei": [None],
                              "investment_value": [100.0]})
        write_cta(self.path)
        self.assertEqual(calculate_portfolio_coverage(frame, PortfolioAggregationMethod.WATS, str(self.path)), 100)
        write_cta(self.path, False)
        self.assertEqual(calculate_portfolio_coverage(frame, PortfolioAggregationMethod.WATS, str(self.path)), 0)


if __name__ == "__main__":
    unittest.main()
