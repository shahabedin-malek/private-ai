"""Tests for appending nested arrivals without renumbering inventory IDs."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.corpus_additive_inventory import append
from scripts.corpus_inventory import build


class AdditiveInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / "repo"
        self.project = self.root / "project"
        self.additions = self.raw / "new"
        self.raw.mkdir()
        self.additions.mkdir()
        with zipfile.ZipFile(self.raw / "original.zip", "w") as archive:
            archive.writestr("README.md", "original")
        self.base = build(self.raw, self.project)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_append_preserves_old_ids_and_writes_all_database_views(self) -> None:
        payloads = {"alpha.zip": b"alpha", "beta.zip": b"beta"}
        for name, content in payloads.items():
            with zipfile.ZipFile(self.additions / name, "w") as archive:
                archive.writestr("README.md", content)
                archive.writestr("src/app.py", b"print('safe')\n")
        before = {row["original_path"]: row["repository_id"] for row in self.base["repositories"]}
        result = append(self.raw, self.project, self.additions, prefix="new")
        self.assertEqual(result["added"], 2)
        # The pre-existing `new/` container directory already occupies an ID in
        # this fixture; additions must allocate only IDs above the current maximum.
        self.assertEqual(result["repository_ids"], ["REPO-0003", "REPO-0004"])

        manifest_path = self.project / "data/manifests/REPO_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        after = {row["original_path"]: row["repository_id"] for row in manifest["repositories"]}
        self.assertEqual({key: after[key] for key in before}, before)
        self.assertEqual(after["new/alpha.zip"], "REPO-0003")
        self.assertEqual(after["new/beta.zip"], "REPO-0004")
        self.assertEqual(next(row for row in manifest["repositories"] if row["repository_id"] == "REPO-0003")["workspace_path"], "data/repos/REPO-0003-alpha.zip")
        self.assertEqual(manifest["totals"]["top_level_items"], 4)

        global_db = sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite")
        try:
            self.assertEqual(global_db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(global_db.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(global_db.execute("SELECT COUNT(*) FROM repositories").fetchone()[0], 4)
            self.assertEqual(global_db.execute("SELECT COUNT(*) FROM repository_files").fetchone()[0], 3)
            rows = global_db.execute("SELECT repository_id,sha256 FROM repository_files WHERE repository_id IN ('REPO-0003','REPO-0004') ORDER BY repository_id").fetchall()
            self.assertEqual(len(rows), 2)
        finally:
            global_db.close()

        for repo_id in ("REPO-0003", "REPO-0004"):
            repo = next(row for row in manifest["repositories"] if row["repository_id"] == repo_id)
            workspace = self.project / repo["workspace_path"]
            self.assertTrue(all((workspace / folder).is_dir() for folder in (
                "source", "extracted", "scraped", "db", "logs", "manifest", "research", "derived")))
            dbs = list((workspace / "db").glob("*.sqlite"))
            self.assertEqual(len(dbs), 1)
            local = sqlite3.connect(dbs[0])
            try:
                self.assertEqual(local.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(local.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(local.execute("SELECT COUNT(*) FROM files").fetchone()[0], 1)
            finally:
                local.close()

    def test_rerun_is_idempotent_and_raw_zip_bytes_are_unchanged(self) -> None:
        with zipfile.ZipFile(self.additions / "alpha.zip", "w") as archive:
            archive.writestr("README.md", "unaltered source")
        source = self.additions / "alpha.zip"
        before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        first = append(self.raw, self.project, self.additions)
        second = append(self.raw, self.project, self.additions)
        self.assertEqual(first["repository_ids"], ["REPO-0003"])
        self.assertEqual(second["repository_ids"], [])
        self.assertEqual(second["added"], 0)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before_hash)

    def test_rejects_path_escape_and_nonregular_additions(self) -> None:
        with self.assertRaises(ValueError):
            append(self.raw, self.project, self.additions, prefix="../escape")
        (self.additions / "nested").mkdir()
        with self.assertRaises(ValueError):
            append(self.raw, self.project, self.additions)


if __name__ == "__main__":
    unittest.main()
