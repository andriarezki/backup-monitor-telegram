import datetime as dt
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

import backup_monitor as bm


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.now = dt.datetime.now()

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, name, size=100, age_h=1):
        p = self.dir / name
        p.write_bytes(b"x" * size)
        t = time.time() - age_h * 3600
        os.utime(p, (t, t))
        return p

    def test_fresh_backup_ok(self):
        self.make("db-1.sql.gz", size=2048, age_h=2)
        r = bm.check({"name": "db", "path": str(self.dir), "pattern": "*.sql.gz"}, self.now)
        self.assertTrue(r.ok, r.detail)

    def test_uses_newest_file(self):
        self.make("old.tar.gz", age_h=100)
        self.make("new.tar.gz", age_h=1)
        r = bm.check({"name": "www", "path": str(self.dir), "pattern": "*.tar.gz"}, self.now)
        self.assertTrue(r.ok)

    def test_stale_backup_fails(self):
        self.make("db.sql.gz", age_h=50)
        r = bm.check({"name": "db", "path": str(self.dir), "max_age_hours": 26}, self.now)
        self.assertFalse(r.ok)
        self.assertIn("50 h ago", r.detail)

    def test_too_small_fails(self):
        self.make("db.sql.gz", size=10)
        r = bm.check({"name": "db", "path": str(self.dir), "min_size_bytes": 1000}, self.now)
        self.assertFalse(r.ok)
        self.assertIn("too small", r.detail)

    def test_missing_path_and_no_match(self):
        r = bm.check({"name": "x", "path": str(self.dir / "nope")}, self.now)
        self.assertFalse(r.ok)
        r = bm.check({"name": "x", "path": str(self.dir), "pattern": "*.zip"}, self.now)
        self.assertFalse(r.ok)

    def test_recursive_search(self):
        sub = self.dir / "2026" / "10"
        sub.mkdir(parents=True)
        p = sub / "dump.sql.gz"
        p.write_bytes(b"x" * 10)
        r = bm.check({"name": "db", "path": str(self.dir), "pattern": "*.sql.gz"}, self.now)
        self.assertTrue(r.ok)


class SummaryAndMainTests(unittest.TestCase):
    def test_summary_lists_failures_first(self):
        text = bm.summary([bm.Result("a", True, "ok"), bm.Result("b", False, "bad")])
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("🔴"))
        self.assertTrue(lines[1].startswith("✘ b"))

    def test_summary_all_ok(self):
        self.assertTrue(bm.summary([bm.Result("a", True, "ok")]).startswith("✅"))

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "f.bak").write_bytes(b"x")
            cfg = Path(d) / "c.json"
            cfg.write_text(json.dumps({"targets": [{"name": "f", "path": d}]}))
            self.assertEqual(bm.main([str(cfg), "--dry-run"]), 0)
            cfg.write_text(json.dumps({"targets": [{"name": "f", "path": d, "max_age_hours": -1}]}))
            self.assertEqual(bm.main([str(cfg), "--dry-run"]), 1)
            cfg.write_text(json.dumps({"targets": []}))
            self.assertEqual(bm.main([str(cfg), "--dry-run"]), 2)

    def test_human_sizes(self):
        self.assertEqual(bm.human(500), "500 B")
        self.assertEqual(bm.human(2048), "2.0 KB")
        self.assertEqual(bm.human(5 * 1024**3), "5.0 GB")


if __name__ == "__main__":
    unittest.main()
