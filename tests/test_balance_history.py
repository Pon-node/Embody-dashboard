import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
import importlib.machinery
import importlib.util


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "from flask import Flask, render_template.py")


def load_app_module():
    loader = importlib.machinery.SourceFileLoader("orch_app", MODULE_PATH)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class BalanceHistoryTests(unittest.TestCase):
    def setUp(self):
        self.module = load_app_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_file = self.module.DB_FILE
        self.module.DB_FILE = os.path.join(self.temp_dir.name, "test.db")
        self.module.db_initialized = False
        self.module.init_db()

    def tearDown(self):
        self.module.DB_FILE = self.original_db_file
        self.temp_dir.cleanup()

    def test_prefers_snapshot_before_threshold(self):
        reference_time = datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)
        older = reference_time - timedelta(hours=26)
        newer = reference_time - timedelta(hours=23)

        self.module.save_balance("addr1", 5.0, timestamp=older)
        self.module.save_balance("addr1", 7.0, timestamp=newer)

        balance = self.module.get_balance_24h_ago("addr1", reference_time=reference_time)
        self.assertEqual(balance, 5.0)

    def test_falls_back_to_first_after_threshold(self):
        reference_time = datetime(2024, 2, 10, 18, 30, tzinfo=timezone.utc)
        after_threshold = reference_time - timedelta(hours=22)

        self.module.save_balance("addr2", 3.5, timestamp=after_threshold)

        balance = self.module.get_balance_24h_ago("addr2", reference_time=reference_time)
        self.assertEqual(balance, 3.5)


if __name__ == "__main__":
    unittest.main()
