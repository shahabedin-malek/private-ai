"""Tests for bounded, provenance-preserving corpus text parsing."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from scripts.corpus_extract import ExtractLimits, run as run_extract
from scripts.corpus_parse import _decode_text, _write_markdown, parse_batch, sensitive_reasons


class CorpusParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_env = {name: os.environ.get(name) for name in ("TMPDIR", "TEMP", "TMP", "SQLITE_TMPDIR")}
        self.original_tempdir = tempfile.tempdir
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.corpus = self.root / "raw"
        self.project = self.root / "project"
        self.corpus.mkdir()
        self.project.mkdir()
        definitions = [
            ("sample.zip", {"README.md": b"# Sample\n\nAPI_KEY=YOUR_API_KEY\n", "src/app.py": b"print('ok')\n"}),
            ("sensitive.zip", {"config.py": b"api_key=real-private-value\n"}),
            ("misleading.zip", {"binary.txt": b"api_key=real-private-value\n"}),
            ("binary.zip", {"image.bin": b"\x00\x01\x02"}),
            ("zero.zip", {"empty.txt": b""}),
            ("invalid-utf8.zip", {"notes.txt": b"invalid: \xff"}),
            ("large.zip", {"large.txt": b"x" * 2048}),
        ]
        repositories = []
        files = []
        for index, (name, members) in enumerate(definitions, start=1):
            source = self.corpus / name
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for member, data in members.items():
                    archive.writestr(member, data)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            size = source.stat().st_size
            repo_id = f"REPO-{index:04d}"
            file_id = f"{repo_id}:{hashlib.sha256(name.encode()).hexdigest()[:20]}"
            workspace = f"{repo_id}-{Path(name).stem}"
            repositories.append({"repository_id": repo_id, "name": name, "original_path": name,
                                 "workspace_path": f"data/repos/{workspace}"})
            files.append({"file_id": file_id, "repository_id": repo_id, "original_path": name,
                          "relative_path": name, "filename": name, "extension": ".zip", "size_bytes": size,
                          "sha256": digest, "mime_type": "application/zip", "detected_format": "zip",
                          "executable": 0, "archive_status": "candidate-not-expanded", "package_type": "archive",
                          "node_type": "file", "discovery_timestamp": "test", "status": "DISCOVERED"})
        manifests = self.project / "data/manifests"
        manifests.mkdir(parents=True)
        (manifests / "REPO_MANIFEST.json").write_text(json.dumps({
            "repositories": repositories, "files": files, "discovery_timestamp": "test"}), encoding="utf-8")
        db_dir = self.project / "data/database"
        db_dir.mkdir(parents=True)
        global_db = db_dir / "private_ai_corpus.sqlite"
        con = sqlite3.connect(global_db)
        con.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE repositories(repository_id TEXT PRIMARY KEY,name TEXT NOT NULL,original_path TEXT NOT NULL,
              workspace_path TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,discovered_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,item_size INTEGER NOT NULL DEFAULT 0,item_sha256 TEXT,
              file_count INTEGER NOT NULL DEFAULT 0,directory_count INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE repository_files(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL REFERENCES repositories(repository_id),
              original_path TEXT NOT NULL,relative_path TEXT NOT NULL,filename TEXT NOT NULL,extension TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,sha256 TEXT,mime_type TEXT NOT NULL,detected_format TEXT NOT NULL,
              executable INTEGER NOT NULL,archive_status TEXT NOT NULL,package_type TEXT NOT NULL,node_type TEXT NOT NULL,
              discovery_timestamp TEXT NOT NULL,status TEXT NOT NULL);
            CREATE TABLE extraction_jobs(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL,source_path TEXT NOT NULL,
              source_sha256 TEXT NOT NULL,detected_format TEXT NOT NULL,status TEXT NOT NULL,destination TEXT,
              started_at TEXT,updated_at TEXT NOT NULL,lease_owner TEXT,lease_expires_at REAL,attempts INTEGER NOT NULL,
              error TEXT,next_action TEXT NOT NULL,pipeline_version TEXT NOT NULL);
            CREATE TABLE extracted_files(record_id TEXT PRIMARY KEY,repository_id TEXT,file_id TEXT,entity_key TEXT NOT NULL,
              payload_json TEXT NOT NULL,source_path TEXT,confidence TEXT,created_at TEXT NOT NULL);
            CREATE TABLE extraction_outputs(extracted_file_id TEXT PRIMARY KEY,source_file_id TEXT NOT NULL,
              repository_id TEXT NOT NULL,member_path TEXT NOT NULL,extracted_path TEXT NOT NULL,parent_archive TEXT NOT NULL,
              depth INTEGER NOT NULL,size_bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,detected_format TEXT NOT NULL,
              status TEXT NOT NULL,tool TEXT NOT NULL,tool_version TEXT NOT NULL,processed_at TEXT NOT NULL);
            CREATE TABLE processing_errors(error_id INTEGER PRIMARY KEY AUTOINCREMENT,repository_id TEXT,file_path TEXT,
              phase TEXT,error TEXT,tool TEXT,tool_version TEXT,timestamp TEXT,retry_count INTEGER,next_action TEXT);
        """)
        for repo, item in zip(repositories, files):
            con.execute("INSERT INTO repositories(repository_id,name,original_path,workspace_path,kind,status,discovered_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (repo["repository_id"], repo["name"], repo["original_path"], Path(repo["workspace_path"]).name,
                         "file", "DISCOVERED", "test", "test"))
            con.execute("INSERT INTO repository_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        tuple(item[key] for key in ("file_id", "repository_id", "original_path", "relative_path", "filename",
                            "extension", "size_bytes", "sha256", "mime_type", "detected_format", "executable",
                            "archive_status", "package_type", "node_type", "discovery_timestamp", "status")))
            workspace = self.project / repo["workspace_path"]
            db_path = workspace / "db" / "item.sqlite"
            db_path.parent.mkdir(parents=True)
            rcon = sqlite3.connect(db_path)
            rcon.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE repository(repository_id TEXT PRIMARY KEY,name TEXT NOT NULL,original_path TEXT NOT NULL,
                  discovered_at TEXT NOT NULL,status TEXT NOT NULL);
                CREATE TABLE files(file_id TEXT PRIMARY KEY,repository_id TEXT NOT NULL REFERENCES repository(repository_id),
                  original_path TEXT NOT NULL,relative_path TEXT NOT NULL,filename TEXT NOT NULL,extension TEXT NOT NULL,
                  size_bytes INTEGER NOT NULL,sha256 TEXT,mime_type TEXT NOT NULL,detected_format TEXT NOT NULL,
                  executable INTEGER NOT NULL,archive_status TEXT NOT NULL,package_type TEXT NOT NULL,node_type TEXT NOT NULL,status TEXT NOT NULL);
                CREATE TABLE file_hashes(file_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL);
                CREATE TABLE extractions(extraction_id INTEGER PRIMARY KEY AUTOINCREMENT,file_id TEXT NOT NULL,status TEXT NOT NULL,
                  destination TEXT,tool TEXT,tool_version TEXT,timestamp TEXT,error TEXT);
                CREATE TABLE archives(file_id TEXT PRIMARY KEY,detected_format TEXT NOT NULL,status TEXT NOT NULL);
                CREATE TABLE provenance(record_id TEXT PRIMARY KEY,file_id TEXT,tool TEXT NOT NULL,tool_version TEXT NOT NULL,
                  pipeline TEXT NOT NULL,timestamp TEXT NOT NULL,source_path TEXT NOT NULL,source_sha256 TEXT,details_json TEXT NOT NULL);
            """)
            rcon.execute("INSERT INTO repository VALUES(?,?,?,?,?)",
                         (repo["repository_id"], repo["name"], repo["original_path"], "test", "DISCOVERED"))
            rcon.execute("INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         tuple(item[key] for key in ("file_id", "repository_id", "original_path", "relative_path", "filename",
                             "extension", "size_bytes", "sha256", "mime_type", "detected_format", "executable",
                             "archive_status", "package_type", "node_type", "status")))
            rcon.execute("INSERT INTO archives VALUES(?,?,?)", (item["file_id"], "zip", "DISCOVERED"))
            rcon.commit()
            rcon.close()
        con.commit()
        con.close()
        for item in files:
            result = run_extract(self.corpus, self.project, repo_id=item["repository_id"], limit=1,
                owner="test", limits=ExtractLimits(min_free_bytes=0, max_total_bytes=1024 * 1024))
            self.assertEqual(result["verified"], 1, result)

    def tearDown(self) -> None:
        self.temp.cleanup()
        tempfile.tempdir = self.original_tempdir
        for name, value in self.original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_cli_routes_tempfile_to_explicit_processing_scratch(self) -> None:
        import subprocess
        import sys

        project = Path(__file__).resolve().parents[1]
        scratch = Path(self.temp.name) / "ssd-scratch"
        parse_batch(self.project, limit=1, max_bytes=1024)
        completed = subprocess.run(
            [sys.executable, str(project / "scripts/corpus_parse.py"), "--project", str(self.project),
             "--scratch-root", str(scratch), "--allow-same-device", "--verify", "--limit", "1"],
            cwd=project, text=True, capture_output=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        startup = json.loads(completed.stderr.splitlines()[0])
        self.assertTrue(startup["probe_verified"])
        self.assertEqual(startup["python_tempdir"], str(scratch / "private-ai-tmp/tmp"))
        self.assertEqual(os.environ.get("TMPDIR"), self.original_env["TMPDIR"])
        self.assertEqual(tempfile.tempdir, self.original_tempdir)

    def _global_rows(self):
        with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
            return con.execute("SELECT extracted_file_id,repository_id,status,source_archive_sha256,markdown_path,markdown_sha256 FROM parsed_content").fetchall()

    def test_parses_text_skips_sensitive_and_mirrors_every_terminal_record(self) -> None:
        report = parse_batch(self.project, limit=20, max_bytes=1024)
        self.assertEqual(report["selected"], 8)
        self.assertEqual(report["counts"], {
            "PARSED": 3, "SENSITIVE": 2, "BINARY": 1, "UNSUPPORTED_ENCODING": 1, "TOO_LARGE": 1})
        self.assertEqual(report["remaining_unparsed"], 0)
        rows = self._global_rows()
        self.assertEqual(len(rows), 8)
        outputs = {}
        with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
            outputs = dict(con.execute("SELECT extracted_file_id,repository_id FROM extraction_outputs"))
        documents = []
        for extracted_id, repo_id, status, _archive_hash, markdown_path, markdown_hash in rows:
            repo_db = self.project / "data/repos" / f"{repo_id}-"  # match by persisted workspace below
            with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
                workspace = con.execute("SELECT workspace_path FROM repositories WHERE repository_id=?", (repo_id,)).fetchone()[0]
            repo_db = self.project / "data/repos" / workspace / "db/item.sqlite"
            with sqlite3.connect(repo_db) as con:
                mirror = con.execute("SELECT status,source_archive_sha256,markdown_path,markdown_sha256 FROM parsed_content WHERE extracted_file_id=?",
                                     (extracted_id,)).fetchone()
            self.assertEqual(mirror, (status, _archive_hash, markdown_path, markdown_hash))
            if markdown_path:
                path = self.project / markdown_path
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), markdown_hash)
                documents.append(path.read_text(encoding="utf-8"))
        combined = "\n".join(documents)
        self.assertIn("API_KEY=YOUR_API_KEY", combined)
        self.assertNotIn("real-private-value", combined)
        self.assertIn('"parser_version": "stdlib-text-v3"', combined)
        sensitive = next(row for row in rows if row[2] == "SENSITIVE")
        with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
            self.assertIn("secret-like-assignment", con.execute(
                "SELECT error FROM parsed_content WHERE extracted_file_id=?", (sensitive[0],)).fetchone()[0])
        self.assertEqual(parse_batch(self.project, limit=20)["selected"], 0)

    def test_global_commit_is_recovered_through_durable_parse_outbox(self) -> None:
        with patch("scripts.corpus_parse._sync_parse_records", side_effect=RuntimeError("injected mirror interruption")):
            report = parse_batch(self.project, limit=1, max_bytes=1024)
        self.assertEqual(report["selected"], 1)
        self.assertTrue(report["errors"])
        with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
            queued = con.execute("SELECT count(*) FROM parse_sync_queue").fetchone()[0]
            status = con.execute("SELECT status FROM parsed_content").fetchone()[0]
        self.assertEqual((queued, status), (1, "PARSED"))

        recovered = parse_batch(self.project, limit=1, max_bytes=1024)
        self.assertEqual(recovered["mirrors_recovered"], 1)
        self.assertEqual(recovered["errors"], [])
        with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
            self.assertEqual(con.execute("SELECT count(*) FROM parse_sync_queue").fetchone()[0], 0)
            extracted_id = con.execute("SELECT extracted_file_id FROM parsed_content").fetchone()[0]
            expected = con.execute("SELECT status,markdown_sha256 FROM parsed_content WHERE extracted_file_id=?",
                                   (extracted_id,)).fetchone()
            workspace = con.execute("SELECT workspace_path FROM repositories WHERE repository_id=?",
                                    (con.execute("SELECT repository_id FROM parsed_content WHERE extracted_file_id=?",
                                                 (extracted_id,)).fetchone()[0],)).fetchone()[0]
        with sqlite3.connect(self.project / "data/repos" / workspace / "db/item.sqlite") as con:
            mirrored = con.execute("SELECT status,markdown_sha256 FROM parsed_content WHERE extracted_file_id=?",
                                   (extracted_id,)).fetchone()
        self.assertEqual(mirrored, expected)
        self.assertEqual(recovered["selected"], 1)
        self.assertEqual(recovered["errors"], [])

    def test_batch_records_commit_and_mirror_as_one_outbox_group(self) -> None:
        report = parse_batch(self.project, limit=8, max_bytes=1024)
        self.assertEqual(report["selected"], 8)
        self.assertEqual(report["errors"], [])
        with sqlite3.connect(self.project / "data/database/private_ai_corpus.sqlite") as con:
            self.assertEqual(con.execute("SELECT count(*) FROM parsed_content").fetchone()[0], 8)
            self.assertEqual(con.execute("SELECT count(*) FROM parse_sync_queue").fetchone()[0], 0)

    def test_sensitive_detector_fails_closed_but_allows_explicit_templates(self) -> None:
        self.assertEqual(sensitive_reasons("API_KEY=YOUR_API_KEY\n"), [])
        self.assertIn("secret-like-assignment", sensitive_reasons("PASSWORD: \"real credential\"\n"))
        self.assertIn("known-token-signature", sensitive_reasons("TOKEN=ghp_" + "A" * 30))
        self.assertIn("private-key-material", sensitive_reasons(
            "-----BEGIN PRIVATE KEY-----\nexample\n-----END PRIVATE KEY-----"))
        self.assertIn("url-credentials", sensitive_reasons("https://user:password@example.invalid/path"))

    def test_zero_byte_text_is_supported_and_markdown_fence_cannot_be_escaped(self) -> None:
        self.assertEqual(_decode_text(b""), ("", None))
        self.assertEqual(sensitive_reasons("api_key=YOUR_API_KEY\n"), [])
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            row = {"extracted_file_id": "fixture", "repository_id": "REPO-0001",
                   "source_file_id": "source", "member_path": "members/fixture.md",
                   "archive_sha256": "a" * 64, "sha256": "b" * 64}
            path, digest = _write_markdown(project, row, "line\n```\n<!-- forged -->\n")
            doc = (project / path).read_text(encoding="utf-8")
            self.assertIn("````\nline\n```\n<!-- forged -->\n````", doc)
            self.assertEqual(hashlib.sha256((project / path).read_bytes()).hexdigest(), digest)
