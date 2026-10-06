"""Focused tests for deterministic, read-only corpus inventorying."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.corpus_inventory import build


class CorpusInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.corpus = self.root / "raw corpus"
        self.output = self.root / "workspace"
        self.corpus.mkdir()
        (self.corpus / "nested project" / "src").mkdir(parents=True)
        (self.corpus / "nested project" / "src" / "hello.py").write_text("print('safe')\n", encoding="utf-8")
        with zipfile.ZipFile(self.corpus / "sample.zip", "w") as archive:
            archive.writestr("docs/readme.txt", "fixture archive is inventoried, not extracted")
        (self.corpus / "opaque.bin").write_bytes(b"\x00\x01opaque\xff")
        try:
            (self.corpus / "link-to-outside").symlink_to(self.root / "outside")
        except OSError:
            self.skipTest("symlinks unavailable on this filesystem")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_inventory_covers_top_level_items_and_records_signatures(self) -> None:
        result = build(self.corpus, self.output)
        manifest = json.loads((self.output / "data/manifests/REPO_MANIFEST.json").read_text())
        self.assertEqual(result["totals"]["top_level_items"], 4)
        self.assertEqual({x["name"] for x in manifest["repositories"] if x["status"] != "MISSING"},
                         {"nested project", "sample.zip", "opaque.bin", "link-to-outside"})
        archive = next(x for x in manifest["files"] if x["filename"] == "sample.zip")
        self.assertEqual(archive["detected_format"], "zip")
        self.assertEqual(archive["archive_status"], "candidate-not-expanded")
        link = next(x for x in manifest["files"] if x["node_type"] == "symlink")
        self.assertIsNone(link["sha256"])
        self.assertEqual(link["detected_format"], "symlink-not-followed")
        self.assertFalse((self.root / "outside").exists())

    def test_repeat_run_preserves_repository_ids_and_database_integrity(self) -> None:
        first = build(self.corpus, self.output)
        manifest_path = self.output / "data/manifests/REPO_MANIFEST.json"
        ids_before = {x["original_path"]: x["repository_id"] for x in first["repositories"]}
        second = build(self.corpus, self.output)
        ids_after = {x["original_path"]: x["repository_id"] for x in second["repositories"]}
        self.assertEqual(ids_before, ids_after)
        manifest = json.loads(manifest_path.read_text())
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        try:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM repositories").fetchone()[0], 4)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM repository_files").fetchone()[0], 4)
        finally:
            con.close()
        for repo in manifest["repositories"]:
            dbs = list((self.output / "data/repos" / f"{repo['repository_id']}-" ).parent.glob(f"{repo['repository_id']}-*/db/*.sqlite"))
            self.assertEqual(len(dbs), 1)
            db = sqlite3.connect(dbs[0])
            try:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            finally:
                db.close()

    def test_raw_corpus_bytes_are_unchanged(self) -> None:
        before = {p.relative_to(self.corpus).as_posix(): p.read_bytes() for p in self.corpus.rglob("*") if p.is_file() and not p.is_symlink()}
        build(self.corpus, self.output)
        after = {p.relative_to(self.corpus).as_posix(): p.read_bytes() for p in self.corpus.rglob("*") if p.is_file() and not p.is_symlink()}
        self.assertEqual(before, after)

    def test_output_inside_raw_corpus_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            build(self.corpus, self.corpus / "generated")

    def test_batch_checkpoints_resume_and_publish_only_after_all_items(self) -> None:
        first = build(self.corpus, self.output, offset=0, limit=2)
        self.assertEqual(first["totals"]["checkpointed_items"], 2)
        self.assertFalse((self.output / "data/manifests/REPO_MANIFEST.json").exists())
        second = build(self.corpus, self.output, offset=2, limit=2)
        self.assertEqual(second["totals"]["top_level_items"], 4)
        self.assertEqual(second["totals"]["regular_files"], 3)
        self.assertTrue((self.output / "data/manifests/REPO_MANIFEST.json").exists())

    def test_modified_file_invalidates_checkpoint_and_refreshes_hash(self) -> None:
        build(self.corpus, self.output)
        path = self.corpus / "nested project" / "src" / "hello.py"
        before = json.loads((self.output / "data/manifests/REPO_MANIFEST.json").read_text())
        old_hash = next(x["sha256"] for x in before["files"] if x["filename"] == "hello.py")
        path.write_text("print('safe')\n# changed\n", encoding="utf-8")
        after = build(self.corpus, self.output)
        new_hash = next(x["sha256"] for x in after["files"] if x["filename"] == "hello.py")
        self.assertNotEqual(old_hash, new_hash)

    def test_removed_item_is_kept_as_missing_and_new_id_is_not_reused(self) -> None:
        build(self.corpus, self.output)
        (self.corpus / "opaque.bin").unlink()
        (self.corpus / "new.txt").write_text("new", encoding="utf-8")
        result = build(self.corpus, self.output)
        item = next(x for x in result["repositories"] if x["original_path"] == "opaque.bin")
        self.assertEqual(item["status"], "MISSING")
        missing_file = next(x for x in result["files"] if x["repository_id"] == item["repository_id"])
        self.assertEqual(missing_file["status"], "MISSING")
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        try:
            row = con.execute("SELECT status FROM repository_files WHERE repository_id=?", (item["repository_id"],)).fetchone()
            self.assertEqual(row[0], "MISSING")
        finally:
            con.close()
        self.assertNotEqual(item["repository_id"], next(x["repository_id"] for x in result["repositories"] if x["original_path"] == "new.txt"))


if __name__ == "__main__":
    unittest.main()
