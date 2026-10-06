"""Tests for hash-verified staging of newly added raw archives."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.corpus_new_batch import SCRATCH_SUBDIR, _count_statuses, _status_rows, extraction_state, queue_priority, stage_sources


class NewBatchStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.corpus = self.root / "repo"
        self.project = self.root / "project"
        self.scratch = self.root / "ssd"
        (self.corpus / "new").mkdir(parents=True)
        (self.project / "data/manifests").mkdir(parents=True)
        self.scratch.mkdir()
        self.sources = []
        for index in range(68):
            name = f"repo-{index:02}.zip"
            path = self.corpus / "new" / name
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("README.md", f"fixture {index}")
            relative = f"new/{name}"
            repo_id = f"REPO-{index + 1:04d}"
            self.sources.append({"repository_id": repo_id, "name": name,
                                 "original_path": relative, "status": "DISCOVERED"})
        files = []
        for repo in self.sources:
            source = self.corpus / repo["original_path"]
            files.append({"repository_id": repo["repository_id"], "original_path": repo["original_path"],
                          "node_type": "file", "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                          "size_bytes": source.stat().st_size})
        (self.project / "data/manifests/REPO_MANIFEST.json").write_text(
            json.dumps({"repositories": self.sources, "files": files}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_stages_all_expected_sources_to_separate_scratch_root(self) -> None:
        staged_corpus, staged_bytes = stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)
        self.assertEqual(staged_corpus, self.scratch / SCRATCH_SUBDIR / "corpus")
        self.assertEqual(staged_bytes, sum((self.corpus / row["original_path"]).stat().st_size for row in self.sources))
        for row in self.sources:
            source = self.corpus / row["original_path"]
            staged = staged_corpus / row["original_path"]
            self.assertEqual(hashlib.sha256(staged.read_bytes()).hexdigest(), hashlib.sha256(source.read_bytes()).hexdigest())

    def test_stages_filesystem_reconciled_count_without_assuming_68(self) -> None:
        keep = self.sources[:3]
        for row in self.sources[3:]:
            (self.corpus / row["original_path"]).unlink()
        manifest_path = self.project / "data/manifests/REPO_MANIFEST.json"
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_path.write_text(json.dumps({
            "repositories": keep,
            "files": [row for row in old["files"] if row["repository_id"] in {repo["repository_id"] for repo in keep}],
        }), encoding="utf-8")
        staged_corpus, staged_bytes = stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)
        self.assertEqual(staged_bytes, sum((self.corpus / row["original_path"]).stat().st_size for row in keep))
        self.assertEqual(sorted(path.name for path in (staged_corpus / "new").iterdir()),
                         sorted(Path(row["original_path"]).name for row in keep))

    def test_rejects_manifest_filesystem_mismatch(self) -> None:
        (self.corpus / "new" / "untracked.zip").write_bytes(b"untracked")
        with self.assertRaisesRegex(ValueError, "source/manifest mismatch"):
            stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)

    def test_cap_is_enforced_and_existing_scratch_is_hash_verified(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceed scratch cap"):
            stage_sources(self.project, self.corpus, self.scratch, 1)
        staged_corpus, _ = stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)
        (staged_corpus / self.sources[0]["original_path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)

    def test_rejects_symlinked_source(self) -> None:
        source = self.corpus / self.sources[0]["original_path"]
        source.unlink()
        source.symlink_to(self.root / "external.zip")
        with self.assertRaisesRegex(ValueError, "not a regular top-level file"):
            stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)

    def test_rejects_duplicate_or_escaping_manifest_paths(self) -> None:
        manifest_path = self.project / "data/manifests/REPO_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["repositories"][0]["original_path"] = "new/../escape.zip"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsafe or unsupported"):
            stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)
        manifest["repositories"][0]["original_path"] = manifest["repositories"][1]["original_path"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate new repository manifest path"):
            stage_sources(self.project, self.corpus, self.scratch, 1024 * 1024)

    def test_paused_state_count_and_database_status_counts(self) -> None:
        repositories = [{"repository_id": "REPO-0001"}, {"repository_id": "REPO-0002"}]
        with patch("scripts.corpus_new_batch.extraction_state", side_effect=[
            {"status": "IN_PROGRESS", "attempts": 2, "error": None, "next_action": "resume", "lease_expires_at": 0},
            {"status": "VERIFIED", "attempts": 1, "error": None, "next_action": "parse", "lease_expires_at": None},
        ]):
            states = _status_rows(repositories, Path("unused"))
        self.assertEqual(states, [("REPO-0001", "PAUSED"), ("REPO-0002", "VERIFIED")])
        self.assertEqual(_count_statuses(states), {"PAUSED": 1, "VERIFIED": 1})

    def test_active_extraction_lease_is_not_reported_as_paused(self) -> None:
        repositories = [{"repository_id": "REPO-0001"}]
        with patch("scripts.corpus_new_batch.extraction_state", return_value={
            "status": "IN_PROGRESS", "attempts": 1, "error": None, "next_action": "extract",
            "lease_expires_at": 4_000_000_000,
        }):
            states = _status_rows(repositories, Path("unused"))
        self.assertEqual(states, [("REPO-0001", "IN_PROGRESS")])
        self.assertEqual(_count_statuses(states), {"IN_PROGRESS": 1})

    def test_queue_prioritizes_new_work_over_paused_retry_work(self) -> None:
        new_repository = {"repository_id": "REPO-0002", "name": "plain-repo.zip"}
        paused_repository = {"repository_id": "REPO-0001", "name": "jev-paused.zip"}
        with patch("scripts.corpus_new_batch.extraction_state", side_effect=[
            None,
            {"status": "IN_PROGRESS", "attempts": 7, "lease_expires_at": 0},
        ]):
            new_priority = queue_priority(new_repository, Path("unused"))
            paused_priority = queue_priority(paused_repository, Path("unused"))
        self.assertLess(new_priority, paused_priority)

    def test_extraction_state_includes_owner_and_lease_expiration(self) -> None:
        db = self.root / "jobs.sqlite"
        con = sqlite3.connect(db)
        con.execute("""CREATE TABLE extraction_jobs (
            repository_id TEXT,status TEXT,attempts INTEGER,error TEXT,next_action TEXT,
            lease_owner TEXT,lease_expires_at REAL
        )""")
        con.execute("INSERT INTO extraction_jobs VALUES(?,?,?,?,?,?,?)",
                    ("REPO-0001", "IN_PROGRESS", 2, None, "extract", "worker-1", 4_000_000_000))
        con.commit()
        con.close()
        state = extraction_state(db, "REPO-0001")
        self.assertIsNotNone(state)
        self.assertEqual(state["lease_owner"], "worker-1")
        self.assertEqual(state["lease_expires_at"], 4_000_000_000)


if __name__ == "__main__":
    unittest.main()
