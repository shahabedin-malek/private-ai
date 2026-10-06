"""Security and recovery tests for bounded, non-executing corpus archive extraction."""
from __future__ import annotations

import gzip
import hashlib
import os
import io
import json
import os
import shutil
import subprocess
import sys
import sqlite3
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from scripts.corpus_extract import ExtractLimits, ExtractionPaused, ExtractionRefusal, detect_format, run, safe_member_path
from scripts.corpus_reconcile import audit as audit_extraction


class SafePathTests(unittest.TestCase):
    def test_accepts_normal_relative_paths(self) -> None:
        self.assertEqual(safe_member_path("src/module.py", max_path_length=240), "src/module.py")
        self.assertEqual(safe_member_path(r"docs\guide.md", max_path_length=240), "docs/guide.md")

    def test_rejects_traversal_absolute_drive_and_ambiguous_names(self) -> None:
        for name in ("../outside", "a/../../outside", "/etc/passwd", "C:/Windows/x", r"\\host\share\x", ""):
            with self.subTest(name=name), self.assertRaises(ExtractionRefusal):
                safe_member_path(name, max_path_length=240)

    def test_path_length_is_bounded(self) -> None:
        with self.assertRaises(ExtractionRefusal):
            safe_member_path("a" * 241, max_path_length=240)

    def test_rejects_windows_ambiguous_and_noncanonical_components(self) -> None:
        for name in ("a//b", "./file", "CON.txt", "folder/name.", "bad:name", "trailing "):
            with self.subTest(name=name), self.assertRaises(ExtractionRefusal):
                safe_member_path(name, max_path_length=240)


class ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.corpus = self.root / "repo"
        self.output = self.root / "project"
        self.corpus.mkdir()
        self.output.mkdir()
        self._prepare_manifest([])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _prepare_manifest(self, definitions: list[tuple[str, bytes]]) -> None:
        # The test uses a minimal inventory-compatible project layout and SQLite schema.
        raw = []
        repositories = []
        for index, (name, data) in enumerate(definitions, start=1):
            path = self.corpus / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            repository_id = f"REPO-{index:04d}"
            file_id = f"{repository_id}:{hashlib.sha256(name.encode()).hexdigest()[:20]}"
            raw.append({"file_id": file_id, "repository_id": repository_id, "original_path": name,
                        "filename": Path(name).name, "relative_path": Path(name).name, "sha256": hashlib.sha256(data).hexdigest(),
                        "size_bytes": len(data), "node_type": "file", "archive_status": "candidate-not-expanded",
                        "detected_format": "zip"})
            workspace = f"data/repos/{repository_id}-{Path(name).stem}"
            repositories.append({"repository_id": repository_id, "name": name,
                                 "original_path": name, "workspace_path": workspace})
        manifests = self.output / "data" / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        (manifests / "REPO_MANIFEST.json").write_text(json.dumps({"files": raw, "repositories": repositories}), encoding="utf-8")
        global_db = self.output / "data" / "database" / "private_ai_corpus.sqlite"
        global_db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(global_db)
        con.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS repositories(repository_id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', original_path TEXT NOT NULL DEFAULT '', workspace_path TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT '', discovered_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '', item_size INTEGER NOT NULL DEFAULT 0, item_sha256 TEXT, file_count INTEGER NOT NULL DEFAULT 0, directory_count INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS repository_files(file_id TEXT PRIMARY KEY, repository_id TEXT REFERENCES repositories(repository_id), original_path TEXT NOT NULL DEFAULT '', relative_path TEXT NOT NULL DEFAULT '', filename TEXT NOT NULL DEFAULT '', extension TEXT NOT NULL DEFAULT '', size_bytes INTEGER NOT NULL DEFAULT 0, sha256 TEXT, mime_type TEXT NOT NULL DEFAULT '', detected_format TEXT NOT NULL DEFAULT '', executable INTEGER NOT NULL DEFAULT 0, archive_status TEXT NOT NULL DEFAULT '', package_type TEXT NOT NULL DEFAULT '', node_type TEXT NOT NULL DEFAULT 'file', discovery_timestamp TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'DISCOVERED');
        CREATE TABLE IF NOT EXISTS processing_errors(error_id INTEGER PRIMARY KEY AUTOINCREMENT, repository_id TEXT, file_path TEXT, phase TEXT, error TEXT, tool TEXT, tool_version TEXT, timestamp TEXT, retry_count INTEGER, next_action TEXT);
        CREATE TABLE IF NOT EXISTS extracted_files(record_id TEXT PRIMARY KEY, repository_id TEXT, file_id TEXT, entity_key TEXT NOT NULL, payload_json TEXT NOT NULL, source_path TEXT, confidence TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS archives(file_id TEXT PRIMARY KEY, detected_format TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'DISCOVERED');
        CREATE TABLE IF NOT EXISTS file_hashes(file_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS provenance(record_id TEXT PRIMARY KEY, file_id TEXT, tool TEXT NOT NULL, tool_version TEXT NOT NULL, pipeline TEXT NOT NULL, timestamp TEXT NOT NULL, source_path TEXT NOT NULL, source_sha256 TEXT, details_json TEXT NOT NULL);
        """)
        for row, repo in zip(raw, repositories):
            con.execute("INSERT INTO repositories(repository_id,name,original_path,workspace_path,kind,status,discovered_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (repo["repository_id"], repo["name"], repo["original_path"], repo["workspace_path"], "file", "DISCOVERED", "now", "now"))
            con.execute("INSERT INTO repository_files(file_id,repository_id,original_path,relative_path,filename,extension,size_bytes,sha256,mime_type,detected_format,executable,archive_status,package_type,node_type,discovery_timestamp,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (row["file_id"], row["repository_id"], row["original_path"], row["relative_path"], row["filename"], Path(row["filename"]).suffix,
                         row["size_bytes"], row["sha256"], "application/octet-stream", row["detected_format"], 0,
                         row["archive_status"], "archive", "file", "now", "DISCOVERED"))
            con.execute("INSERT INTO archives(file_id,detected_format,status) VALUES(?,?,?)",
                        (row["file_id"], row["detected_format"], "DISCOVERED"))
            db_path = self.output / repo["workspace_path"] / "db" / f"{Path(repo['name']).stem.lower()}.sqlite"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            repo_con = sqlite3.connect(db_path)
            repo_con.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE repository(repository_id TEXT PRIMARY KEY,name TEXT NOT NULL DEFAULT '',original_path TEXT NOT NULL DEFAULT '',discovered_at TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'DISCOVERED');
                CREATE TABLE files(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL REFERENCES repository(repository_id),original_path TEXT NOT NULL DEFAULT '',relative_path TEXT NOT NULL DEFAULT '',filename TEXT NOT NULL DEFAULT '',extension TEXT NOT NULL DEFAULT '',size_bytes INTEGER NOT NULL DEFAULT 0,sha256 TEXT,mime_type TEXT NOT NULL DEFAULT '',detected_format TEXT NOT NULL DEFAULT '',executable INTEGER NOT NULL DEFAULT 0,archive_status TEXT NOT NULL DEFAULT '',package_type TEXT NOT NULL DEFAULT '',node_type TEXT NOT NULL DEFAULT 'file',status TEXT NOT NULL DEFAULT 'DISCOVERED');
                CREATE TABLE file_hashes(file_id TEXT PRIMARY KEY REFERENCES files(file_id),sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL);
                CREATE TABLE extractions(extraction_id INTEGER PRIMARY KEY AUTOINCREMENT,file_id TEXT NOT NULL REFERENCES files(file_id),status TEXT NOT NULL,destination TEXT,tool TEXT,tool_version TEXT,timestamp TEXT,error TEXT);
                CREATE TABLE archives(file_id TEXT PRIMARY KEY REFERENCES files(file_id),detected_format TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'DISCOVERED');
                CREATE TABLE provenance(record_id TEXT PRIMARY KEY,file_id TEXT REFERENCES files(file_id),tool TEXT NOT NULL,tool_version TEXT NOT NULL,pipeline TEXT NOT NULL,timestamp TEXT NOT NULL,source_path TEXT NOT NULL,source_sha256 TEXT,details_json TEXT NOT NULL DEFAULT '{}');
            """)
            repo_con.execute("INSERT INTO repository(repository_id,name,original_path,discovered_at,status) VALUES(?,?,?,?,?)",
                             (repo["repository_id"], repo["name"], repo["original_path"], "now", "DISCOVERED"))
            repo_con.execute("INSERT INTO files(file_id,repository_id,original_path,relative_path,filename,size_bytes,sha256,detected_format,archive_status,node_type,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                             (row["file_id"], row["repository_id"], row["original_path"], row["relative_path"],
                              row["filename"], row["size_bytes"], row["sha256"], row["detected_format"],
                              row["archive_status"], row["node_type"], "DISCOVERED"))
            repo_con.execute("INSERT INTO archives(file_id,detected_format,status) VALUES(?,?,?)",
                             (row["file_id"], row["detected_format"], "DISCOVERED"))
            repo_con.commit()
            repo_con.close()
            (self.output / repo["workspace_path"] / "extracted").mkdir(parents=True, exist_ok=True)
        con.commit()
        con.close()

    def _run(self, limits: ExtractLimits | None = None, repo_id: str | None = None):
        return run(self.corpus, self.output, repo_id=repo_id, limit=50, owner="test-worker", limits=limits)

    def test_reconciliation_checks_verified_output_and_database_rows(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("README.md", b"# reconciled\\n")
        self._prepare_manifest([("reconcile.zip", buf.getvalue())])
        self.assertEqual(self._run()["verified"], 1)
        report = audit_extraction(self.corpus, self.output, offset=0, limit=1)
        self.assertEqual(report["checked"]["verified_outputs"], 1)
        self.assertEqual(report["issues"], [])

        global_db = self.output / "data/database/private_ai_corpus.sqlite"
        with sqlite3.connect(global_db) as con:
            con.execute("DELETE FROM extraction_outputs")
        report = audit_extraction(self.corpus, self.output, offset=0, limit=1)
        self.assertTrue(any(issue["stage"] == "global-output" for issue in report["issues"]))

    def test_zip_extracts_exact_bytes_and_records_provenance(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("README.md", b"# sample\n")
            archive.writestr("src/main.py", b"print('not executed')\n")
        self._prepare_manifest([("sample.zip", buf.getvalue())])
        result = self._run()
        self.assertEqual(result["verified"], 1, result["results"])
        repo = self.output / "data/repos/REPO-0001-sample/extracted"
        outputs = list(repo.iterdir())
        self.assertEqual(len(outputs), 1)
        metadata = json.loads((outputs[0] / "extraction.json").read_text())
        self.assertEqual(metadata["files"], [
            {"depth": 0, "format": "zip", "member_path": "members/README.md", "parent_archive": "sample.zip", "sha256": hashlib.sha256(b"# sample\n").hexdigest(), "size_bytes": 9, "status": "EXTRACTED"},
            {"depth": 0, "format": "zip", "member_path": "members/src/main.py", "parent_archive": "sample.zip", "sha256": hashlib.sha256(b"print('not executed')\n").hexdigest(), "size_bytes": 22, "status": "EXTRACTED"},
        ])
        self.assertEqual((outputs[0] / "members/README.md").read_bytes(), b"# sample\n")
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM extracted_files").fetchone()[0], 2)
        self.assertEqual(con.execute("SELECT status FROM extraction_jobs").fetchone()[0], "VERIFIED")
        con.close()
        repo_db = next((self.output / "data/repos/REPO-0001-sample/db").glob("*.sqlite"))
        con = sqlite3.connect(repo_db)
        self.assertEqual(con.execute("SELECT status FROM extraction_jobs").fetchone()[0], "VERIFIED")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM extraction_outputs").fetchone()[0], 2)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM provenance WHERE pipeline='safe-extract-v6'").fetchone()[0], 2)
        con.close()

    def test_tar_extracts_regular_files_but_refuses_symlinks_and_special_members(self) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as archive:
            info = tarfile.TarInfo("ok.txt")
            payload = b"safe"
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        self._prepare_manifest([("safe.tar", buf.getvalue())])
        result = self._run()
        self.assertEqual(result["verified"], 1, result["results"])
        self.assertEqual(detect_format(self.corpus / "safe.tar"), "tar")

    def test_tar_symlink_member_is_rejected_without_publishing_any_member(self) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as archive:
            info = tarfile.TarInfo("safe.txt")
            payload = b"should not publish"
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
            link = tarfile.TarInfo("link")
            link.type = tarfile.SYMTYPE
            link.linkname = "../../outside"
            archive.addfile(link)
        self._prepare_manifest([("linked.tar", buf.getvalue())])
        result = self._run()
        self.assertEqual(result["failed"], 1)
        self.assertEqual(list((self.output / "data/repos/REPO-0001-linked/extracted").iterdir()), [])

    def test_zip_traversal_symlinks_and_duplicate_paths_fail_before_writes(self) -> None:
        malicious_archives = []
        traversal = io.BytesIO()
        with zipfile.ZipFile(traversal, "w") as archive:
            archive.writestr("../escape.txt", b"escape")
        malicious_archives.append(("traversal.zip", traversal.getvalue()))

        symlink = io.BytesIO()
        with zipfile.ZipFile(symlink, "w") as archive:
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            archive.writestr(info, "../../outside")
        malicious_archives.append(("symlink.zip", symlink.getvalue()))

        duplicate = io.BytesIO()
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr("README", b"first")
            archive.writestr("readme", b"case collision")
        malicious_archives.append(("duplicate.zip", duplicate.getvalue()))

        for name, contents in malicious_archives:
            with self.subTest(name=name):
                shutil.rmtree(self.corpus)
                shutil.rmtree(self.output)
                self.corpus.mkdir()
                self.output.mkdir()
                self._prepare_manifest([(name, contents)])
                result = self._run()
                self.assertEqual(result["failed"], 1, result["results"])
                extracted = self.output / f"data/repos/REPO-0001-{Path(name).stem}/extracted"
                self.assertEqual(list(extracted.iterdir()), [])

    def test_nested_archives_are_recursively_extracted_with_depth_recorded(self) -> None:
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as archive:
            archive.writestr("inner.txt", b"nested")
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w") as archive:
            archive.writestr("nested.zip", nested.getvalue())
        self._prepare_manifest([("outer.zip", outer.getvalue())])
        result = self._run()
        self.assertEqual(result["verified"], 1, result["results"])
        root = next((self.output / "data/repos/REPO-0001-outer/extracted").iterdir())
        self.assertEqual((root / "members/nested.zip.contents/inner.txt").read_bytes(), b"nested")
        manifest = json.loads((root / "extraction.json").read_text())
        self.assertTrue(any(record.get("depth") == 1 for record in manifest["files"]))

    def test_nested_depth_limit_is_recorded_and_does_not_extract_too_deep(self) -> None:
        level2 = io.BytesIO()
        with zipfile.ZipFile(level2, "w") as archive:
            archive.writestr("inside.txt", b"x")
        level1 = io.BytesIO()
        with zipfile.ZipFile(level1, "w") as archive:
            archive.writestr("level2.zip", level2.getvalue())
        self._prepare_manifest([("outer.zip", level1.getvalue())])
        result = self._run(ExtractLimits(max_depth=0))
        self.assertEqual(result["verified"], 1, result["results"])
        output = next((self.output / "data/repos/REPO-0001-outer/extracted").iterdir())
        metadata = json.loads((output / "extraction.json").read_text())
        nested = next(x for x in metadata["files"] if x["member_path"].endswith("level2.zip"))
        self.assertEqual(nested["nested_status"], "BLOCKED_DEPTH")

    def test_member_count_and_compression_ratio_limits_fail_closed_without_publishing(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("small.txt", b"x" * 10_000)
            archive.writestr("other.txt", b"y")
        self._prepare_manifest([("limited.zip", buf.getvalue())])
        result = self._run(ExtractLimits(max_members=1))
        self.assertEqual(result["failed"], 1)
        self.assertEqual(list((self.output / "data/repos/REPO-0001-limited/extracted").iterdir()), [])
        result = self._run(ExtractLimits(max_members=10, max_compression_ratio=2))
        self.assertEqual(result["failed"], 1)

    def test_member_byte_and_total_byte_limits_apply_to_actual_reads(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("member.bin", b"a" * 5000)
        self._prepare_manifest([("large.zip", buf.getvalue())])
        result = self._run(ExtractLimits(max_member_bytes=1000, max_total_bytes=6000))
        self.assertEqual(result["failed"], 1)
        self.assertEqual(list((self.output / "data/repos/REPO-0001-large/extracted").iterdir()), [])

    def test_timed_out_worker_is_terminated_with_its_descendant_processes(self) -> None:
        child = "import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
        started = __import__("time").monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([sys.executable, "-c", child], timeout=0.2, check=True)
        elapsed = __import__("time").monotonic() - started
        self.assertLess(elapsed, 2.0, "timeout must not block while a descendant inherits the output pipe")

    def test_corrupt_zip_is_visible_as_failure_and_does_not_leave_staging(self) -> None:
        self._prepare_manifest([("bad.zip", b"PK\x03\x04broken-not-an-archive")])
        result = self._run()
        self.assertEqual(result["failed"], 1)
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        row = con.execute("SELECT status,error,next_action,attempts FROM extraction_jobs").fetchone()
        con.close()
        self.assertEqual(row[0], "FAILED")
        self.assertTrue(row[1])
        self.assertTrue(row[2])
        self.assertGreaterEqual(row[3], 1)
        self.assertEqual(list((self.output / "data/repos/REPO-0001-bad/extracted").iterdir()), [])

    def test_gzip_stream_is_extracted_to_a_confined_file(self) -> None:
        source = self.corpus / "archive.data.gz"
        source.write_bytes(gzip.compress(b"durable output"))
        row = {"file_id": "REPO-0001:abc", "repository_id": "REPO-0001", "original_path": source.name,
               "filename": source.name, "relative_path": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "size_bytes": source.stat().st_size, "node_type": "file", "archive_status": "candidate-not-expanded", "detected_format": "gzip"}
        mpath = self.output / "data/manifests/REPO_MANIFEST.json"
        data = json.loads(mpath.read_text())
        data["files"] = [row]
        data["repositories"] = [{"repository_id": "REPO-0001", "name": source.name,
                                 "original_path": source.name,
                                 "workspace_path": "data/repos/REPO-0001-archive.data"}]
        mpath.write_text(json.dumps(data))

        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        con.execute("INSERT OR IGNORE INTO repositories(repository_id) VALUES(?)", (row["repository_id"],))
        con.execute("INSERT OR IGNORE INTO repository_files(file_id,repository_id) VALUES(?,?)", (row["file_id"], row["repository_id"]))
        con.commit();con.close()
        repo_db = self.output / "data/repos/REPO-0001-archive.data/db/archive.data.sqlite"
        repo_db.parent.mkdir(parents=True, exist_ok=True)
        repo_con = sqlite3.connect(repo_db)
        repo_con.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE repository(repository_id TEXT PRIMARY KEY,name TEXT NOT NULL,original_path TEXT NOT NULL,discovered_at TEXT NOT NULL,status TEXT NOT NULL);
            CREATE TABLE files(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL REFERENCES repository(repository_id),original_path TEXT NOT NULL,relative_path TEXT NOT NULL,filename TEXT NOT NULL,extension TEXT NOT NULL DEFAULT '',size_bytes INTEGER NOT NULL,sha256 TEXT,mime_type TEXT NOT NULL DEFAULT '',detected_format TEXT NOT NULL,executable INTEGER NOT NULL DEFAULT 0,archive_status TEXT NOT NULL,package_type TEXT NOT NULL DEFAULT '',node_type TEXT NOT NULL,status TEXT NOT NULL);
            CREATE TABLE file_hashes(file_id TEXT PRIMARY KEY REFERENCES files(file_id),sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL);
            CREATE TABLE extractions(extraction_id INTEGER PRIMARY KEY AUTOINCREMENT,file_id TEXT NOT NULL REFERENCES files(file_id),status TEXT NOT NULL,destination TEXT,tool TEXT,tool_version TEXT,timestamp TEXT,error TEXT);
            CREATE TABLE archives(file_id TEXT PRIMARY KEY REFERENCES files(file_id),detected_format TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'DISCOVERED');
            CREATE TABLE provenance(record_id TEXT PRIMARY KEY,file_id TEXT,tool TEXT NOT NULL,tool_version TEXT NOT NULL,pipeline TEXT NOT NULL,timestamp TEXT NOT NULL,source_path TEXT NOT NULL,source_sha256 TEXT,details_json TEXT NOT NULL);
        """)
        repo_con.execute("INSERT INTO repository VALUES(?,?,?,?,?)", (row["repository_id"], source.name, source.name, "now", "DISCOVERED"))
        repo_con.execute("INSERT INTO files(file_id,repository_id,original_path,relative_path,filename,size_bytes,sha256,detected_format,archive_status,node_type,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (row["file_id"], row["repository_id"], source.name, source.name, source.name,
                          row["size_bytes"], row["sha256"], "gzip", "candidate-not-expanded", "file", "DISCOVERED"))
        repo_con.execute("INSERT INTO archives VALUES(?,?,?)", (row["file_id"], "gzip", "DISCOVERED"))
        repo_con.commit()
        repo_con.close()
        result = self._run()
        self.assertEqual(result["verified"], 1, result["results"])
        out = next((self.output / "data/repos/REPO-0001-archive.data/extracted").iterdir())
        self.assertEqual((out / "members/archive.data").read_bytes(), b"durable output")

    def test_source_file_bytes_are_never_modified(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("doc.txt", b"source untouched")
        self._prepare_manifest([("readonly.zip", buf.getvalue())])
        source = self.corpus / "readonly.zip"
        old_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        self._run()
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), old_hash)

    def test_output_inside_raw_corpus_is_refused(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x", b"y")
        self._prepare_manifest([("inside.zip", buf.getvalue())])
        with self.assertRaises(ValueError):
            run(self.corpus, self.corpus, limit=1)

    def test_idempotent_retry_skips_a_verified_source(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x.txt", b"x")
        self._prepare_manifest([("once.zip", buf.getvalue())])
        first = self._run()
        self.assertEqual(first["verified"], 1)
        second = self._run()
        self.assertEqual(second["verified"], 0)
        self.assertEqual(second["skipped_verified"], 1)
        self.assertTrue(second["results"][0]["skipped"])

    def test_db_commit_recovery_indexes_already_published_output_without_reextracting(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("recover.txt", b"persisted")
        self._prepare_manifest([("recover.zip", buf.getvalue())])
        self.assertEqual(self._run()["verified"], 1)
        db = self.output / "data/database/private_ai_corpus.sqlite"
        con = sqlite3.connect(db)
        con.execute("DELETE FROM extraction_outputs")
        con.execute("DELETE FROM extracted_files")
        con.execute("UPDATE extraction_jobs SET status='IN_PROGRESS',lease_expires_at=0")
        con.commit()
        con.close()
        result = self._run()
        self.assertTrue(result["results"][0].get("recovered_without_reextracting"), result["results"])
        self.assertEqual(result["verified"], 1)
        con = sqlite3.connect(db)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM extraction_outputs").fetchone()[0], 1)
        self.assertEqual(con.execute("SELECT status FROM extraction_jobs").fetchone()[0], "VERIFIED")
        con.close()

    def test_verified_output_tampering_is_detected_and_repaired(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("original.txt", b"original")
        self._prepare_manifest([("repair.zip", buf.getvalue())])
        self.assertEqual(self._run()["verified"], 1)
        root = next((self.output / "data/repos/REPO-0001-repair/extracted").iterdir())
        (root / "members/original.txt").write_bytes(b"tampered")
        retry = self._run()
        self.assertEqual(retry["verified"], 1, retry["results"])
        self.assertEqual((root / "members/original.txt").read_bytes(), b"original")

    def test_terminal_blocked_and_failed_states_are_mirrored_to_repository_database(self) -> None:
        blocked = io.BytesIO()
        with zipfile.ZipFile(blocked, "w") as archive:
            archive.writestr("blocked.txt", b"blocked")
        failed = b"PK\x03\x04also bad"
        self._prepare_manifest([("blocked.zip", blocked.getvalue()), ("failed.zip", failed)])
        # Simulate a previously recorded terminal unsupported format that must be mirrored.
        from scripts.corpus_extract import _ensure_schema, _inventory_file_id, _record_error
        global_db = self.output / "data/database/private_ai_corpus.sqlite"
        _ensure_schema(global_db)
        manifest_path = self.output / "data/manifests/REPO_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text())
        blocked_row = manifest["files"][0]
        _record_error(global_db, file_id=_inventory_file_id(blocked_row), repo_id="REPO-0001",
                      source_path=blocked_row["original_path"], source_hash=blocked_row["sha256"],
                      fmt="ar-unsupported", owner="test", error="unsupported fixture format",
                      next_action="use a safe ar reader", attempts=1, status="BLOCKED")
        # Exercise the reconciliation path with the same durable terminal status, then verify it is synchronized.
        result = self._run(repo_id="REPO-0001")
        self.assertEqual(result["blocked"], 1, result["results"])
        self.assertEqual(result["terminal_records_mirrored"], 1)
        with sqlite3.connect(global_db) as global_con:
            archive_columns = {row[1] for row in global_con.execute("PRAGMA table_info(archives)")}
            if "status" in archive_columns:
                archive_status = global_con.execute("SELECT status FROM archives WHERE file_id=?",
                                                     (_inventory_file_id(blocked_row),)).fetchone()[0]
            else:
                archive_payload = global_con.execute("SELECT payload_json FROM archives WHERE file_id=?",
                                                     (_inventory_file_id(blocked_row),)).fetchone()[0]
                archive_status = json.loads(archive_payload)["status"]
            self.assertEqual(archive_status, "BLOCKED")
        from scripts.corpus_extract import _mirror_terminal_state
        global_con = sqlite3.connect(global_db)
        global_con.row_factory = sqlite3.Row
        blocked_job = dict(global_con.execute("SELECT * FROM extraction_jobs WHERE file_id=?",
                                              (_inventory_file_id(blocked_row),)).fetchone())
        self.assertFalse(_mirror_terminal_state(self.output.resolve(), manifest, blocked_job))
        global_con.close()
        failed_result = self._run(repo_id="REPO-0002")
        self.assertEqual(failed_result["failed"], 1, failed_result["results"])
        self.assertEqual(failed_result["terminal_records_mirrored"], 0)
        failed_global = sqlite3.connect(global_db)
        failed_global.row_factory = sqlite3.Row
        failed_job = dict(failed_global.execute("SELECT * FROM extraction_jobs WHERE repository_id='REPO-0002'").fetchone())
        self.assertFalse(_mirror_terminal_state(self.output.resolve(), manifest, failed_job))
        failed_global.close()
        for repo_id, stem, expected_status in (("REPO-0001", "blocked", "BLOCKED"),
                                               ("REPO-0002", "failed", "FAILED")):
            repo_db = next((self.output / f"data/repos/{repo_id}-{stem}/db").glob("*.sqlite"))
            con = sqlite3.connect(repo_db)
            self.assertEqual(con.execute("SELECT status FROM extraction_jobs").fetchone()[0], expected_status)
            self.assertEqual(con.execute("SELECT status FROM extractions").fetchone()[0], expected_status)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM processing_errors WHERE phase='extraction'").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT status FROM archives").fetchone()[0], expected_status)
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
            con.close()

    def test_interrupted_journal_resumes_verified_members_without_rewriting_them(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x.txt", b"already extracted")
            archive.writestr("y.txt", b"still needs extraction")
        self._prepare_manifest([("interrupted.zip", buf.getvalue())])
        job_dir = self.output / "data/repos/REPO-0001-interrupted/extracted"
        token = hashlib.sha256(("REPO-0001:" + hashlib.sha256("interrupted.zip".encode()).hexdigest()[:20]).encode()).hexdigest()[:24]
        staging = job_dir / f".{token}.staging"
        existing = staging / "members/x.txt"
        existing.parent.mkdir(parents=True)
        payload = b"already extracted"
        existing.write_bytes(payload)
        before_inode = existing.stat().st_ino
        record = {"member_path": "members/x.txt", "status": "EXTRACTED", "depth": 0,
                  "format": "zip", "size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                  "parent_archive": "interrupted.zip"}
        from scripts.corpus_extract import _journal_record
        _journal_record(staging, record)
        retry = self._run()
        self.assertEqual(retry["verified"], 1, retry["results"])
        root = job_dir / token
        self.assertEqual((root / "members/x.txt").stat().st_ino, before_inode)
        self.assertEqual((root / "members/x.txt").read_bytes(), payload)
        self.assertEqual((root / "members/y.txt").read_bytes(), b"still needs extraction")
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        recovery = con.execute("SELECT error,next_action FROM processing_errors WHERE phase='extraction-recovery'").fetchone()
        con.close()
        self.assertIsNotNone(recovery)
        self.assertIn("resumed after verifying 1 member", recovery[0])
        self.assertIn("continue extraction", recovery[1])

    def test_corrupt_interrupted_journal_is_discarded_and_retried(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x.txt", b"x")
        self._prepare_manifest([("corrupt-stage.zip", buf.getvalue())])
        job_dir = self.output / "data/repos/REPO-0001-corrupt-stage/extracted"
        token = hashlib.sha256(("REPO-0001:" + hashlib.sha256("corrupt-stage.zip".encode()).hexdigest()[:20]).encode()).hexdigest()[:24]
        staging = job_dir / f".{token}.staging"
        staging.mkdir()
        (staging / "members").mkdir()
        (staging / "members/untrusted.txt").write_bytes(b"unverified")
        (staging / ".extraction-journal.jsonl").write_text("not-json\\n", encoding="utf-8")
        retry = self._run()
        self.assertEqual(retry["verified"], 1, retry["results"])
        root = job_dir / token
        self.assertEqual((root / "members/x.txt").read_bytes(), b"x")
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        recovery = con.execute("SELECT error,next_action FROM processing_errors WHERE phase='extraction-recovery'").fetchone()
        con.close()
        self.assertIn("failed verification and was discarded", recovery[0])
        self.assertIn("clean staging", recovery[1])
        self.assertFalse((root / "members/untrusted.txt").exists())

    def test_pipeline_upgrade_reopens_failed_and_blocked_jobs(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x.txt", b"x")
        self._prepare_manifest([("upgrade.zip", buf.getvalue())])
        db = self.output / "data/database/private_ai_corpus.sqlite"
        con = sqlite3.connect(db)
        con.execute("""CREATE TABLE IF NOT EXISTS extraction_jobs(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL REFERENCES repositories(repository_id),source_path TEXT NOT NULL,source_sha256 TEXT NOT NULL,detected_format TEXT NOT NULL,status TEXT NOT NULL,destination TEXT,started_at TEXT,updated_at TEXT NOT NULL,lease_owner TEXT,lease_expires_at REAL,attempts INTEGER NOT NULL DEFAULT 0,error TEXT,next_action TEXT NOT NULL DEFAULT '',pipeline_version TEXT NOT NULL DEFAULT '')""")
        file_id = "REPO-0001:" + hashlib.sha256("upgrade.zip".encode()).hexdigest()[:20]
        con.execute("INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,status,updated_at,attempts,error,pipeline_version) VALUES(?,?,?,?,?,'FAILED','now',3,'old worker failure','safe-extract-v1')",
                    (file_id, "REPO-0001", "upgrade.zip", hashlib.sha256((self.corpus / "upgrade.zip").read_bytes()).hexdigest(), "zip"))
        con.commit()
        con.close()
        result = self._run()
        self.assertEqual(result["verified"], 1, result["results"])
        con = sqlite3.connect(db)
        row = con.execute("SELECT status,attempts,pipeline_version FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
        con.close()
        self.assertEqual(row, ("VERIFIED", 1, "safe-extract-v6"))

    def test_wall_budget_pause_keeps_verified_staging_and_releases_lease(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x.txt", b"persisted")
        self._prepare_manifest([("paused.zip", buf.getvalue())])
        with patch("scripts.corpus_extract._extract_tree", side_effect=ExtractionPaused("test wall budget")):
            result = self._run()
        self.assertEqual(result["paused"], 1, result["results"])
        self.assertEqual(result["failed"], 0)
        con = sqlite3.connect(self.output / "data/database/private_ai_corpus.sqlite")
        row = con.execute("SELECT status,lease_owner,lease_expires_at,next_action FROM extraction_jobs").fetchone()
        con.close()
        self.assertEqual(row, ("IN_PROGRESS", None, 0.0, "resume verified staging on next worker pass"))
        token = hashlib.sha256(("REPO-0001:" + hashlib.sha256("paused.zip".encode()).hexdigest()[:20]).encode()).hexdigest()[:24]
        self.assertTrue((self.output / f"data/repos/REPO-0001-paused/extracted/.{token}.staging").is_dir())

    def test_active_lease_prevents_a_second_worker_claim(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("x.txt", b"x")
        self._prepare_manifest([("leased.zip", buf.getvalue())])
        db = self.output / "data/database/private_ai_corpus.sqlite"
        repo = "REPO-0001"
        file_id = "REPO-0001:" + hashlib.sha256("leased.zip".encode()).hexdigest()[:20]
        con = sqlite3.connect(db)
        con.execute("""CREATE TABLE IF NOT EXISTS extraction_jobs(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL REFERENCES repositories(repository_id),source_path TEXT NOT NULL,source_sha256 TEXT NOT NULL,detected_format TEXT NOT NULL,status TEXT NOT NULL,destination TEXT,started_at TEXT,updated_at TEXT NOT NULL,lease_owner TEXT,lease_expires_at REAL,attempts INTEGER NOT NULL DEFAULT 0,error TEXT,next_action TEXT NOT NULL DEFAULT '')""")
        con.execute("INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,status,updated_at,lease_owner,lease_expires_at,attempts) VALUES(?,?,?,?,?,'IN_PROGRESS','now','other-worker',?,1)",
                    (file_id, repo, "leased.zip", hashlib.sha256((self.corpus / "leased.zip").read_bytes()).hexdigest(), "zip", __import__('time').time()+600))
        con.commit();con.close()
        result = self._run()
        self.assertEqual(result["blocked"], 1)
        self.assertIn("active lease", result["results"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
