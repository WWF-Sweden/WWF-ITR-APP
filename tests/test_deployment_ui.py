"""Check deployment controls through the running Streamlit interface."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from db import database

ROOT = Path(__file__).resolve().parents[1]


class DeploymentUITests(unittest.TestCase):
    def test_database_controls_and_upload_warnings_follow_mode(self):
        for mode in (None, "cloud", "local"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                with patch.dict(os.environ), patch.object(database, "_DB_DIR", directory):
                    os.environ.pop("ITR_DEPLOYMENT", None)
                    if mode is not None:
                        os.environ["ITR_DEPLOYMENT"] = mode
                    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
                    self.assertFalse(app.exception)
                    source = next(r for r in app.radio if r.label == "Data Source")
                    self.assertEqual("Load from Database" in source.options, mode == "local")
                    expected = "database enabled" if mode == "local" else "database disabled"
                    self.assertTrue(any(expected in c.value for c in app.caption))
                    for option in ("Upload Custom Data", "Pre-scored Data (4b format)"):
                        source.set_value(option).run()
                        self.assertFalse(app.exception)
                        warning = any("Dataset database disabled" in w.value for w in app.warning)
                        self.assertEqual(warning, mode != "local")
                    self.assertEqual(list(Path(directory).iterdir()), [])

    def test_sample_review_hides_saving_in_demo_and_allows_it_locally(self):
        from utils import data_loader
        for mode in (None, "local"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                with patch.dict(os.environ), patch.object(database, "_DB_DIR", directory), patch.object(
                    data_loader, "download_sample_data", return_value=(
                        str(ROOT / "data/data_provider_example_360.xlsx"),
                        str(ROOT / "data/example_portfolio_360.csv"),
                    ),
                ):
                    os.environ.pop("ITR_DEPLOYMENT", None)
                    if mode:
                        os.environ["ITR_DEPLOYMENT"] = mode
                    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
                    app.button(key="load_data_btn").click().run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.session_state["data_loaded"])
                    save_buttons = [b for b in app.button if b.key == "save_to_db"]
                    self.assertEqual(len(save_buttons), 1 if mode else 0)
                    if mode:
                        save_buttons[0].click().run()
                        self.assertFalse(app.exception)
                        self.assertEqual(database.list_datasets()[0]["name"], "my_dataset")
                    else:
                        self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
