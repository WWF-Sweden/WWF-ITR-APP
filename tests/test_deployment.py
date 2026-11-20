"""Deployment-mode and database-access regression tests."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from deployment import is_local_deployment
from db import database


class DeploymentModeTests(unittest.TestCase):
    def test_deployment_values(self):
        cases = [
            (None, False), ("", False), (" ", False), ("cloud", False),
            ("demo", False), ("lokal", False), ("local-other", False),
            ("local", True), ("LOCAL", True), (" Local ", True),
            ("\tlocal\n", True),
        ]
        for value, expected in cases:
            with self.subTest(value=value), patch.dict(os.environ):
                os.environ.pop("ITR_DEPLOYMENT", None)
                if value is not None:
                    os.environ["ITR_DEPLOYMENT"] = value
                self.assertIs(is_local_deployment(), expected)

    def test_database_can_be_imported_before_utils(self):
        # A fresh interpreter detects circular imports hidden by test discovery.
        result = subprocess.run(
            [sys.executable, "-c", "import db.database; import utils.data_loader"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class DatabaseDeploymentTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.data_dir = Path(directory.name) / "data"
        path_patch = patch.object(database, "_DB_DIR", str(self.data_dir))
        path_patch.start()
        self.addCleanup(path_patch.stop)
        env_patch = patch.dict(os.environ)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        os.environ.pop("ITR_DEPLOYMENT", None)
        self.portfolio = pd.DataFrame({
            "company_id": ["company-1"], "investment_value": [100.0],
        })
        self.fundamental = pd.DataFrame({
            "company_id": ["company-1"], "company_name": ["Example Company"],
        })
        self.targets = pd.DataFrame({
            "company_id": ["company-1"], "end_year": [2030],
        })

    def save_example(self):
        database.save_dataset(
            "example", self.portfolio, self.fundamental,
            self.targets, "Test dataset",
        )

    def database_operations(self):
        return [
            ("path", database.get_db_path),
            ("initialise", database.init_db),
            ("list", database.list_datasets),
            ("load", lambda: database.load_dataset("example")),
            ("save", self.save_example),
            ("update", lambda: database.update_table(
                "example", "portfolio", self.portfolio,
            )),
            ("delete", lambda: database.delete_dataset("example")),
        ]

    def test_disabled_operations_do_not_create_storage(self):
        for value in (None, "", "cloud", "lokal"):
            with self.subTest(mode=value):
                os.environ.pop("ITR_DEPLOYMENT", None)
                if value is not None:
                    os.environ["ITR_DEPLOYMENT"] = value
                for name, operation in self.database_operations():
                    with self.subTest(operation=name):
                        with self.assertRaises(database.DatabaseDisabledError):
                            operation()
                        self.assertFalse(self.data_dir.exists())

    def test_existing_database_is_inaccessible_and_unchanged_in_demo_mode(self):
        os.environ["ITR_DEPLOYMENT"] = "local"
        self.save_example()
        db_path = Path(database.get_db_path())
        original_bytes = db_path.read_bytes()
        os.environ.pop("ITR_DEPLOYMENT")
        for name, operation in self.database_operations():
            with self.subTest(operation=name):
                with self.assertRaises(database.DatabaseDisabledError):
                    operation()
                self.assertEqual(db_path.read_bytes(), original_bytes)
        os.environ["ITR_DEPLOYMENT"] = "local"
        pd.testing.assert_frame_equal(
            database.load_dataset("example")["portfolio"], self.portfolio,
        )

    def test_local_mode_supports_database_lifecycle(self):
        os.environ["ITR_DEPLOYMENT"] = "local"
        self.assertEqual(database.list_datasets(), [])
        self.assertTrue((self.data_dir / database._DB_NAME).is_file())
        self.save_example()
        datasets = database.list_datasets()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]["name"], "example")
        self.assertEqual(datasets[0]["description"], "Test dataset")
        loaded = database.load_dataset("example")
        for key, expected in (
            ("portfolio", self.portfolio),
            ("fundamental_data", self.fundamental),
            ("target_data", self.targets),
        ):
            with self.subTest(table=key):
                pd.testing.assert_frame_equal(loaded[key], expected)
        updated_portfolio = self.portfolio.copy()
        updated_portfolio["investment_value"] = [250.0]
        database.update_table("example", "portfolio", updated_portfolio)
        pd.testing.assert_frame_equal(
            database.load_dataset("example")["portfolio"], updated_portfolio,
        )
        database.delete_dataset("example")
        self.assertEqual(database.list_datasets(), [])
        with self.assertRaises(KeyError):
            database.load_dataset("example")


if __name__ == "__main__":
    unittest.main()
