#!/usr/bin/env python3
"""Parse extracted corpus text into bounded Markdown without executing corpus content."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    from .processing_workspace import DEFAULT_ROOT, initialize_workspace
except ImportError:
    from processing_workspace import DEFAULT_ROOT, initialize_workspace

PARSER_VERSION = "stdlib-text-v3"
MIGRATION = "corpus-parse-v4"
SUPPORTED_TEXT_EXTENSIONS = {
    ".c", ".cc", ".cfg", ".cjs", ".conf", ".cpp", ".cs", ".css", ".csv", ".go",
    ".h", ".hpp", ".htm", ".html", ".ini", ".java", ".js", ".jsx", ".json",
    ".json5", ".jsonc", ".jsonl", ".kt", ".md", ".mdx", ".mjs", ".php", ".py",
    ".r", ".rb", ".rs", ".rst", ".scala", ".scss", ".sh", ".sql", ".svg", ".swift",
    ".text", ".toml", ".ts", ".tsx", ".txt", ".vue", ".xml", ".yaml", ".yml", ".zsh",
}
SUPPORTED_TEXT_NAMES = {"authors", "changelog", "copying", "dockerfile", "license", "makefile", "notice", "procfile"}
SECRET_ASSIGNMENT = re.compile(
    r"(?im)(?:^|[^A-Za-z0-9])([A-Za-z0-9_-]*(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|private[_-]?key|secret|token))\s*[:=]\s*(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;#]+)"
)
PLACEHOLDER = re.compile(
    r"(?i)^(?:|none|null|nil|undefined|changeme|change_me|replace(?:_me)?|your(?:_|-).+|"
    r"<[^>]+>|\$\{[^}]+\}|\$\([^)]+\)|\{\{[^}]+\}\}|\*{3,}|x{3,}|"
    r"example(?:_value)?|dummy|fake|test|insert[_-].+|redacted|n/?a)$"
)
SECRET_PATTERNS = (
    ("private-key-material", re.compile(
        r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*?-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----", re.DOTALL)),
    ("known-token-signature", re.compile(
        r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
        r"xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,})\b")),
    ("jwt-signature", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("url-credentials", re.compile(r"https?://[^:/@\s]+:[^@/\s]+@", re.IGNORECASE)),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{12,}={0,2}")),
)
_MIGRATED_DBS: set[str] = set()
_REPO_DB_CACHE: dict[tuple[str, str], Path] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    try:
        yield con
    finally:
        con.close()


def confined_path(project: Path, relative: Path, *, must_exist: bool = False) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path is not a confined relative path")
    current = project
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink in path: {current}")
    resolved = current.resolve(strict=must_exist)
    resolved.relative_to(project)
    return resolved


def migrate(db: Path) -> None:
    key = str(db.resolve())
    if key in _MIGRATED_DBS:
        return
    migration = "add archive/member/Markdown hash provenance to parsed_content"
    reason = "Separate source archive hash, extracted member hash, and generated Markdown hash for verifiable provenance."
    try:
        with connect(db) as con, con:
            con.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY, timestamp TEXT NOT NULL, migration TEXT NOT NULL,
                reason TEXT NOT NULL, status TEXT NOT NULL, error TEXT
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS parsed_content (
                extracted_file_id TEXT PRIMARY KEY REFERENCES extraction_outputs(extracted_file_id),
                repository_id TEXT NOT NULL, source_file_id TEXT NOT NULL, member_path TEXT NOT NULL,
                source_archive_sha256 TEXT NOT NULL DEFAULT '', member_sha256 TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL, markdown_path TEXT, markdown_sha256 TEXT,
                char_count INTEGER NOT NULL DEFAULT 0, parser TEXT NOT NULL, parser_version TEXT NOT NULL,
                processed_at TEXT NOT NULL, error TEXT
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS parse_sync_queue (
                extracted_file_id TEXT PRIMARY KEY REFERENCES parsed_content(extracted_file_id),
                repository_id TEXT NOT NULL, enqueued_at TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0, last_error TEXT
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_parse_sync_queue_repo ON parse_sync_queue(repository_id, enqueued_at)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_parsed_content_version_status ON parsed_content(parser_version, status)")
            columns = {row["name"] for row in con.execute("PRAGMA table_info(parsed_content)")}
            for name, declaration in (
                ("source_archive_sha256", "TEXT NOT NULL DEFAULT ''"),
                ("member_sha256", "TEXT NOT NULL DEFAULT ''"),
                ("markdown_sha256", "TEXT"),
            ):
                if name not in columns:
                    con.execute(f"ALTER TABLE parsed_content ADD COLUMN {name} {declaration}")
            con.execute("""INSERT INTO schema_migrations(version,timestamp,migration,reason,status,error)
                VALUES(?,?,?,?,?,NULL) ON CONFLICT(version) DO UPDATE SET timestamp=excluded.timestamp,
                migration=excluded.migration,reason=excluded.reason,status='SUCCESS',error=NULL
                WHERE schema_migrations.status!='SUCCESS'""",
                        (MIGRATION, now(), migration + "; add a durable global-to-item mirror outbox and lookup indexes",
                         reason + " Persist global parser state and mirror intent atomically; recover per-item mirrors after interruption.", "SUCCESS"))
        _MIGRATED_DBS.add(key)
    except sqlite3.Error as exc:
        try:
            with connect(db) as con, con:
                con.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY, timestamp TEXT NOT NULL, migration TEXT NOT NULL,
                    reason TEXT NOT NULL, status TEXT NOT NULL, error TEXT
                )""")
                con.execute("INSERT OR REPLACE INTO schema_migrations VALUES(?,?,?,?,?,?)",
                            (MIGRATION, now(), migration, reason, "FAILED", type(exc).__name__))
        except sqlite3.Error:
            pass
        raise


def repository_db(project: Path, repo_id: str, extracted_id: str) -> Path:
    key = (str(project), repo_id)
    cached = _REPO_DB_CACHE.get(key)
    if cached is not None and cached.is_file() and not cached.is_symlink():
        return cached
    with connect(project / "data/database/private_ai_corpus.sqlite") as con:
        row = con.execute("SELECT workspace_path FROM repositories WHERE repository_id=?", (repo_id,)).fetchone()
    if row is None or not row["workspace_path"]:
        raise FileNotFoundError(f"workspace path missing for {repo_id}")
    workspace = confined_path(project, Path("data/repos") / row["workspace_path"], must_exist=True)
    matches = []
    for candidate in sorted((workspace / "db").glob("*.sqlite")):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        try:
            with connect(candidate) as con:
                table_names = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "extraction_outputs" in table_names and con.execute(
                        "SELECT 1 FROM extraction_outputs WHERE extracted_file_id=?", (extracted_id,)).fetchone():
                    matches.append(candidate)
        except sqlite3.Error:
            continue
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one per-item DB with output {extracted_id}; found {len(matches)}")
    _REPO_DB_CACHE[key] = matches[0]
    return matches[0]


def _is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.fullmatch(value.strip().strip("\"'`.,;).")))


def sensitive_reasons(text: str) -> list[str]:
    reasons = [label for label, pattern in SECRET_PATTERNS if pattern.search(text)]
    if any(not _is_placeholder(match.group(2)) for match in SECRET_ASSIGNMENT.finditer(text)):
        reasons.append("secret-like-assignment")
    return list(dict.fromkeys(reasons))


def _decode_text(raw: bytes) -> tuple[str | None, str | None]:
    if not raw:
        return "", None
    if b"\x00" in raw:
        return None, "BINARY"
    try:
        text = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return None, "UNSUPPORTED_ENCODING"
    if any((ord(char) < 32 and char not in "\t\n\r\f") or ord(char) == 127 for char in text):
        return None, "BINARY"
    return text, None


def _supported(member_path: str) -> bool:
    name = Path(member_path).name.lower()
    return Path(name).suffix.lower() in SUPPORTED_TEXT_EXTENSIONS or name in SUPPORTED_TEXT_NAMES


def _provenance_json(metadata: dict[str, str]) -> str:
    return json.dumps(metadata, sort_keys=True, ensure_ascii=True).replace("--", "\\u002d\\u002d")


def _write_markdown(project: Path, row: sqlite3.Row, content: str) -> tuple[str, str]:
    fence_size = max(3, max((len(m.group(0)) for m in re.finditer(r"`+", content)), default=2) + 1)
    fence = "`" * fence_size
    metadata = {
        "extracted_file_id": row["extracted_file_id"], "repository_id": row["repository_id"],
        "source_file_id": row["source_file_id"], "member_path": row["member_path"],
        "source_archive_sha256": row["archive_sha256"] or "", "member_sha256": row["sha256"],
        "parser": "corpus_parse.py", "parser_version": PARSER_VERSION,
    }
    metadata_json = _provenance_json(metadata)
    document = (f"# {html.escape(row['member_path'])}\n\n"
                f"<!-- private-ai-provenance: {metadata_json} -->\n\n"
                f"## Extracted content\n\n{fence}\n{content}"
                f"{'' if content.endswith(chr(10)) else chr(10)}{fence}\n")
    payload = document.encode("utf-8")
    relative = Path("data/knowledge/files") / row["repository_id"] / f"{row['extracted_file_id']}.md"
    target = confined_path(project, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = confined_path(project, relative)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(relative), hashlib.sha256(payload).hexdigest()


def _verify_markdown(project: Path, row: sqlite3.Row, record: sqlite3.Row) -> bool:
    try:
        if (record["repository_id"] != row["repository_id"]
                or record["source_file_id"] != row["source_file_id"]
                or record["member_path"] != row["member_path"]
                or record["source_archive_sha256"] != (row["archive_sha256"] or "")
                or record["member_sha256"] != row["sha256"]
                or record["parser_version"] != PARSER_VERSION
                or not record["markdown_path"] or not record["markdown_sha256"]):
            return False
        markdown = confined_path(project, Path(record["markdown_path"]), must_exist=True)
        if not markdown.is_file():
            return False
        digest = hashlib.sha256(markdown.read_bytes()).hexdigest()
        if digest != record["markdown_sha256"]:
            return False
        metadata = {"extracted_file_id": row["extracted_file_id"], "repository_id": row["repository_id"],
            "source_file_id": row["source_file_id"], "member_path": row["member_path"],
            "source_archive_sha256": row["archive_sha256"] or "", "member_sha256": row["sha256"],
            "parser": "corpus_parse.py", "parser_version": PARSER_VERSION}
        encoded = _provenance_json(metadata)
        return f"<!-- private-ai-provenance: {encoded} -->" in markdown.read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        return False


def _parse_member(project: Path, row: sqlite3.Row, *, max_bytes: int) -> dict[str, Any]:
    source = confined_path(project, Path(row["extracted_path"]), must_exist=True)
    if not source.is_file():
        raise ValueError("extracted member is not a regular file")
    if source.stat().st_size != row["size_bytes"]:
        return {"status": "SOURCE_MISMATCH", "error": "member size differs from extraction provenance"}
    digest = hashlib.sha256()
    buffer = bytearray()
    total = 0
    too_large = False
    with source.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            total += len(chunk)
            if not too_large:
                if total <= max_bytes:
                    buffer.extend(chunk)
                else:
                    too_large = True
                    buffer.clear()
    if (digest.hexdigest(), total) != (row["sha256"], row["size_bytes"]):
        return {"status": "SOURCE_MISMATCH", "error": "member bytes disagree with extraction record"}
    if too_large:
        return {"status": "TOO_LARGE", "error": f"member exceeds {max_bytes} byte parser limit"}
    text, reason = _decode_text(bytes(buffer))
    if reason:
        return {"status": reason, "error": "member is not safely decodable UTF-8 text"}
    assert text is not None
    if not _supported(row["member_path"]):
        return {"status": "UNSUPPORTED_TYPE", "error": "no bounded text parser for this member type"}
    sensitive = sensitive_reasons(text)
    if sensitive:
        return {"status": "SENSITIVE", "error": "sensitive content signals: " + ", ".join(sensitive)}
    markdown_path, markdown_hash = _write_markdown(project, row, text)
    return {"status": "PARSED", "error": None, "markdown_path": markdown_path,
            "markdown_sha256": markdown_hash, "char_count": len(text)}


PARSED_COLUMNS = ("extracted_file_id", "repository_id", "source_file_id", "member_path", "source_archive_sha256",
                  "member_sha256", "status", "markdown_path", "markdown_sha256", "char_count", "parser",
                  "parser_version", "processed_at", "error")


def _save_many(db: Path, rows: list[tuple[Any, ...]], *, enqueue_mirror: bool = False) -> None:
    if not rows:
        return
    with connect(db) as con, con:
        columns = {row["name"] for row in con.execute("PRAGMA table_info(parsed_content)")}
        values_by_name = {
            "extracted_file_id": 0, "repository_id": 1, "source_file_id": 2, "member_path": 3,
            "source_archive_sha256": 4, "member_sha256": 5, "status": 6, "markdown_path": 7,
            "markdown_sha256": 8, "char_count": 9, "parser": 10, "parser_version": 11,
            "processed_at": 12, "error": 13,
        }
        compatibility = {"source_sha256": 5, "text_sha256": 8, "redactions": None}
        selected = [name for name in (*values_by_name, *compatibility) if name in columns]
        updates = [name for name in selected if name != "extracted_file_id"]
        sql = (f"INSERT INTO parsed_content({','.join(selected)}) VALUES({','.join('?' for _ in selected)}) "
               f"ON CONFLICT(extracted_file_id) DO UPDATE SET "
               + ",".join(f"{name}=excluded.{name}" for name in updates))
        for values in rows:
            record = dict(values_by_name)
            for name, index in compatibility.items():
                if name in columns and index is not None:
                    record[name] = index
            con.execute(sql, tuple(values[record[name]] if name in record else 0 for name in selected))
        if enqueue_mirror:
            con.executemany("""INSERT INTO parse_sync_queue(extracted_file_id,repository_id,enqueued_at,attempt_count,last_error)
                VALUES(?,?,?,0,NULL) ON CONFLICT(extracted_file_id) DO UPDATE SET
                repository_id=excluded.repository_id,enqueued_at=excluded.enqueued_at""",
                [(values[0], values[1], now()) for values in rows])


def _save(db: Path, values: tuple[Any, ...], *, enqueue_mirror: bool = False) -> None:
    _save_many(db, [values], enqueue_mirror=enqueue_mirror)


def _sync_parse_records(project: Path, global_db: Path, extracted_file_ids: list[str]) -> None:
    """Mirror a set of globally committed rows by repository, then acknowledge the outbox."""
    ids = list(dict.fromkeys(extracted_file_ids))
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    with connect(global_db) as con:
        rows = con.execute(f"SELECT {','.join(PARSED_COLUMNS)} FROM parsed_content "
                            f"WHERE extracted_file_id IN ({placeholders}) ORDER BY repository_id,extracted_file_id", ids).fetchall()
        queued = {row["extracted_file_id"]: row["repository_id"] for row in con.execute(
            f"SELECT extracted_file_id,repository_id FROM parse_sync_queue WHERE extracted_file_id IN ({placeholders})", ids)}
    if len(rows) != len(ids) or any(queued.get(row["extracted_file_id"]) != row["repository_id"] for row in rows):
        raise RuntimeError("parse mirror outbox no longer matches its global records")
    groups: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        groups.setdefault(row["repository_id"], []).append(row)
    for repo_id, group in groups.items():
        per_db = repository_db(project, repo_id, group[0]["extracted_file_id"])
        migrate(per_db)
        _save_many(per_db, [tuple(row[field] for field in PARSED_COLUMNS) for row in group])
        group_ids = [row["extracted_file_id"] for row in group]
        group_placeholders = ",".join("?" for _ in group_ids)
        with connect(per_db) as con:
            mirrors = {row["extracted_file_id"]: tuple(row[field] for field in PARSED_COLUMNS)
                       for row in con.execute(f"SELECT {','.join(PARSED_COLUMNS)} FROM parsed_content "
                                              f"WHERE extracted_file_id IN ({group_placeholders})", group_ids)}
        expected = {row["extracted_file_id"]: tuple(row[field] for field in PARSED_COLUMNS) for row in group}
        if mirrors != expected:
            raise RuntimeError("per-item parser mirror verification failed")
    with connect(global_db) as con, con:
        con.executemany("DELETE FROM parse_sync_queue WHERE extracted_file_id=?", [(item,) for item in ids])


def _sync_parse_record(project: Path, global_db: Path, extracted_file_id: str) -> None:
    _sync_parse_records(project, global_db, [extracted_file_id])


def _drain_parse_sync_queue(project: Path, global_db: Path, *, limit: int) -> tuple[int, list[dict[str, str]]]:
    with connect(global_db) as con:
        ids = [row["extracted_file_id"] for row in con.execute(
            "SELECT extracted_file_id FROM parse_sync_queue ORDER BY enqueued_at,extracted_file_id LIMIT ?", (limit,))]
    if not ids:
        return 0, []
    try:
        _sync_parse_records(project, global_db, ids)
        return len(ids), []
    except Exception as exc:
        with connect(global_db) as con, con:
            con.executemany("UPDATE parse_sync_queue SET attempt_count=attempt_count+1,last_error=? WHERE extracted_file_id=?",
                            [(type(exc).__name__, item) for item in ids])
        return 0, [{"extracted_file_id": ids[0], "error": f"mirror recovery failed: {type(exc).__name__}"}]


def _record_error(db: Path, row: sqlite3.Row, error: str) -> None:
    with connect(db) as con, con:
        columns = {item["name"] for item in con.execute("PRAGMA table_info(processing_errors)")}
        values = {
            "repository_id": row["repository_id"], "file_id": row["source_file_id"],
            "file_path": row["member_path"], "phase": "parsing", "error": error,
            "tool": "corpus_parse.py", "tool_version": PARSER_VERSION, "timestamp": now(),
            "retry_count": 1,
            "next_action": "repair parser/output/DB inconsistency and retry this extracted member",
        }
        selected = [name for name in values if name in columns]
        con.execute(f"INSERT INTO processing_errors({','.join(selected)}) VALUES({','.join('?' for _ in selected)})",
                    tuple(values[name] for name in selected))


def _pending_count(db: Path) -> int:
    with connect(db) as con:
        return int(con.execute("""SELECT count(*) FROM extraction_outputs o LEFT JOIN parsed_content p
            ON p.extracted_file_id=o.extracted_file_id AND p.parser_version=?
            WHERE o.status='EXTRACTED' AND (p.extracted_file_id IS NULL OR p.status='FAILED'
              OR p.repository_id!=o.repository_id OR p.source_file_id!=o.source_file_id
              OR p.member_path!=o.member_path OR p.member_sha256!=o.sha256
              OR p.source_archive_sha256!=COALESCE((SELECT f.sha256 FROM repository_files f WHERE f.file_id=o.source_file_id),''))""",
            (PARSER_VERSION,)).fetchone()[0])


def verify_parsed_corpus(project: Path, *, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    project = project.resolve(strict=True)
    if offset < 0 or limit < 1:
        raise ValueError("offset must be non-negative and limit must be positive")
    db = project / "data/database/private_ai_corpus.sqlite"
    issues: list[dict[str, str]] = []
    checked = 0
    counts: dict[str, int] = {}
    with connect(db) as con:
        rows = con.execute("""SELECT p.*,o.repository_id AS output_repository_id,
            o.source_file_id AS output_source_file_id,o.member_path AS output_member_path,
            o.sha256 AS output_member_sha256,o.extracted_path,o.size_bytes AS output_member_size,
            f.sha256 AS output_archive_sha256,f.size_bytes AS source_archive_size,
            r.workspace_path FROM parsed_content p JOIN extraction_outputs o USING(extracted_file_id)
            LEFT JOIN repository_files f ON f.file_id=o.source_file_id
            JOIN repositories r ON r.repository_id=o.repository_id
            WHERE p.parser_version=? ORDER BY p.repository_id,p.member_path LIMIT ? OFFSET ?""",
            (PARSER_VERSION, limit, offset)).fetchall()
    for row in rows:
        checked += 1
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        identity = (row["repository_id"], row["source_file_id"], row["member_path"], row["member_sha256"], row["source_archive_sha256"])
        expected = (row["output_repository_id"], row["output_source_file_id"], row["output_member_path"],
                    row["output_member_sha256"], row["output_archive_sha256"] or "")
        if identity != expected:
            issues.append({"extracted_file_id": row["extracted_file_id"], "stage": "global-provenance",
                           "detail": "parse identity/hash does not match extraction/global source records"})
        verification_row = dict(row)
        verification_row.update({"archive_sha256": row["output_archive_sha256"], "sha256": row["output_member_sha256"]})
        repo_db = repository_db(project, row["repository_id"], row["extracted_file_id"])
        with connect(repo_db) as local:
            mirror = local.execute("SELECT * FROM parsed_content WHERE extracted_file_id=?",
                                   (row["extracted_file_id"],)).fetchone()
        fields = ("repository_id", "source_file_id", "member_path", "source_archive_sha256", "member_sha256",
                  "status", "markdown_path", "markdown_sha256", "parser", "parser_version", "error")
        if mirror is None or tuple(mirror[field] for field in fields) != tuple(row[field] for field in fields):
            issues.append({"extracted_file_id": row["extracted_file_id"], "stage": "per-item-mirror",
                           "detail": "global and per-item parse provenance/status differ"})
        if row["status"] == "PARSED":
            if not _verify_markdown(project, verification_row, row):
                issues.append({"extracted_file_id": row["extracted_file_id"], "stage": "markdown",
                               "detail": "Markdown missing, outside project, hash-mismatched, or provenance-invalid"})
        elif row["markdown_path"] is not None or row["markdown_sha256"] is not None:
            issues.append({"extracted_file_id": row["extracted_file_id"], "stage": "unexpected-markdown",
                           "detail": "non-PARSED state unexpectedly references a Markdown output"})
    return {"offset": offset, "next_offset": offset + checked, "checked": checked,
            "candidate_total": checked, "status_counts": counts, "issues": issues}


def _parse_batch_locked(project: Path, *, limit: int = 25, max_bytes: int = 2 * 1024 * 1024,
                        max_wall_seconds: float = 60.0) -> dict[str, Any]:
    project = project.resolve(strict=True)
    if limit < 1 or max_bytes < 1 or max_wall_seconds <= 0:
        raise ValueError("limit, max_bytes and max_wall_seconds must be positive")
    db = project / "data/database/private_ai_corpus.sqlite"
    migrate(db)
    with connect(db) as con:
        rows = con.execute("""SELECT o.*,
            (SELECT f.sha256 FROM repository_files f WHERE f.file_id=o.source_file_id) AS archive_sha256,
            p.extracted_file_id AS parsed_id,p.status AS parse_status,p.markdown_path AS parse_markdown_path,
            p.markdown_sha256 AS parse_markdown_sha256,p.member_sha256 AS parse_member_sha256,
            p.source_archive_sha256 AS parse_archive_sha256,p.repository_id AS parse_repository_id,
            p.source_file_id AS parse_source_file_id,p.member_path AS parse_member_path,
            p.parser_version AS parse_parser_version,p.error AS parse_error
            FROM extraction_outputs o LEFT JOIN parsed_content p
              ON p.extracted_file_id=o.extracted_file_id AND p.parser_version=?
            WHERE o.status='EXTRACTED' AND (p.extracted_file_id IS NULL OR p.status='FAILED' OR
              p.repository_id!=o.repository_id OR p.source_file_id!=o.source_file_id OR
              p.member_path!=o.member_path OR p.parser_version!=? OR p.member_sha256!=o.sha256 OR
              p.source_archive_sha256!=COALESCE(
                (SELECT f.sha256 FROM repository_files f WHERE f.file_id=o.source_file_id),''))
            ORDER BY o.repository_id,o.member_path LIMIT ?""", (PARSER_VERSION, PARSER_VERSION, limit)).fetchall()
    counts: dict[str, int] = {}
    errors: list[dict[str, str]] = []
    synced_before, sync_errors = _drain_parse_sync_queue(project, db, limit=limit)
    errors.extend(sync_errors)
    if sync_errors:
        return {"selected": 0, "counts": counts, "errors": errors,
                "mirrors_recovered": synced_before, "remaining_unparsed": _pending_count(db)}
    started = time.monotonic()
    processed = 0
    pending_records: list[tuple[Any, ...]] = []
    pending_ids: list[str] = []
    last_flush = started
    flush_failed = False

    def flush_pending() -> bool:
        nonlocal last_flush, flush_failed
        if not pending_records:
            return True
        try:
            _save_many(db, pending_records, enqueue_mirror=True)
            _sync_parse_records(project, db, pending_ids)
            pending_records.clear()
            pending_ids.clear()
            last_flush = time.monotonic()
            return True
        except Exception as exc:
            flush_failed = True
            errors.append({"extracted_file_id": pending_ids[0] if pending_ids else "batch",
                           "error": f"batch commit/mirror failed: {type(exc).__name__}"})
            return False

    for row in rows:
        if processed and time.monotonic() - started >= max_wall_seconds:
            break
        per_db: Path | None = None
        try:
            if row["parsed_id"] is not None:
                per_db = repository_db(project, row["repository_id"], row["extracted_file_id"])
                migrate(per_db)
                with connect(per_db) as con:
                    mirror = con.execute("SELECT * FROM parsed_content WHERE extracted_file_id=?", (row["extracted_file_id"],)).fetchone()
                if (mirror is not None and row["parse_status"] == "PARSED"
                        and row["parse_member_sha256"] == row["sha256"]
                        and row["parse_archive_sha256"] == (row["archive_sha256"] or "")
                        and row["parse_repository_id"] == row["repository_id"]
                        and row["parse_source_file_id"] == row["source_file_id"]
                        and row["parse_member_path"] == row["member_path"]
                        and row["parse_parser_version"] == PARSER_VERSION
                        and _verify_markdown(project, row, mirror)):
                    counts["PARSED"] = counts.get("PARSED", 0) + 1
                    processed += 1
                    continue
            result = _parse_member(project, row, max_bytes=max_bytes)
            if result["status"] != "PARSED":
                stale_markdown = project / "data/knowledge/files" / row["repository_id"] / f"{row['extracted_file_id']}.md"
                try:
                    stale_markdown = confined_path(project, stale_markdown.relative_to(project))
                    if stale_markdown.is_file():
                        stale_markdown.unlink()
                except FileNotFoundError:
                    pass
            error = result.get("error")
            values = (row["extracted_file_id"], row["repository_id"], row["source_file_id"], row["member_path"],
                row["archive_sha256"] or "", row["sha256"], result["status"], result.get("markdown_path"),
                result.get("markdown_sha256"), result.get("char_count", 0), "corpus_parse.py", PARSER_VERSION, now(), error)
            pending_records.append(values)
            pending_ids.append(row["extracted_file_id"])
            counts[result["status"]] = counts.get(result["status"], 0) + 1
            processed += 1
            if result["status"] == "SOURCE_MISMATCH":
                errors.append({"extracted_file_id": row["extracted_file_id"], "error": error or "source mismatch"})
        except Exception as exc:
            processed += 1
            error = f"{type(exc).__name__}: {exc}"
            errors.append({"extracted_file_id": row["extracted_file_id"], "error": error})
            try:
                if per_db is None:
                    per_db = repository_db(project, row["repository_id"], row["extracted_file_id"])
                _record_error(per_db, row, error)
            except sqlite3.Error:
                pass
            try:
                _record_error(db, row, error)
            except sqlite3.Error:
                pass
            failed_values = (row["extracted_file_id"], row["repository_id"], row["source_file_id"],
                row["member_path"], row["archive_sha256"] or "", row["sha256"], "FAILED", None, None,
                0, "corpus_parse.py", PARSER_VERSION, now(), error)
            pending_records.append(failed_values)
            pending_ids.append(row["extracted_file_id"])
        if len(pending_records) >= 128 or time.monotonic() - last_flush >= 15:
            if not flush_pending():
                break
    if pending_records and not flush_failed:
        flush_pending()
    return {"selected": processed, "counts": counts, "errors": errors,
            "mirrors_recovered": synced_before, "remaining_unparsed": _pending_count(db)}


def parse_batch(project: Path, *, limit: int = 25, max_bytes: int = 2 * 1024 * 1024,
                max_wall_seconds: float = 60.0) -> dict[str, Any]:
    project = project.resolve(strict=True)
    if limit < 1 or max_bytes < 1 or max_wall_seconds <= 0:
        raise ValueError("limit, max_bytes and max_wall_seconds must be positive")
    lock_dir = project / ".progress"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "CORPUS-0006-parser.lock"
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _parse_batch_locked(project, limit=limit, max_bytes=max_bytes,
                                       max_wall_seconds=max_wall_seconds)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--scratch-root", type=Path, default=DEFAULT_ROOT,
                        help="SSD scratch workspace; Python and SQLite temporary files are routed here")
    parser.add_argument("--allow-same-device", action="store_true",
                        help="explicitly permit a non-SSD scratch root on the project filesystem")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--max-mb", type=int, default=2)
    parser.add_argument("--max-wall-seconds", type=float, default=60.0)
    parser.add_argument("--all", action="store_true", help="process bounded batches until completion or a durable error")
    parser.add_argument("--verify", action="store_true", help="verify parsed Markdown and global/per-item database mirrors")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--audit", action="store_true", help="audit existing parsed rows in bounded batches")
    args = parser.parse_args()
    try:
        scratch_status = initialize_workspace(args.scratch_root, project=args.project,
                                              require_separate_device=not args.allow_same_device)
        print(json.dumps({"event": "processing_workspace_verified", "root": scratch_status["root"],
                          "python_tempdir": scratch_status["python_tempdir"],
                          "device": scratch_status["root_device"],
                          "project_device": scratch_status["project_device"],
                          "used_bytes": scratch_status["used_bytes"],
                          "free_bytes": scratch_status["free_bytes"],
                          "quota_severity": scratch_status["severity"],
                          "cap_bytes": scratch_status["cap_bytes"],
                          "probe_verified": scratch_status["probe_verified"]}),
              file=sys.stderr, flush=True)
        if args.verify:
            report = verify_parsed_corpus(args.project, offset=args.offset, limit=args.limit)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 1 if report["issues"] else 0
        if args.audit:
            reports = []
            current_offset = args.offset
            while True:
                report = verify_parsed_corpus(args.project, offset=current_offset, limit=args.limit)
                reports.append(report)
                print(json.dumps(report, sort_keys=True), flush=True)
                current_offset = report["next_offset"]
                if report["checked"] == 0 or report["issues"]:
                    break
            return 1 if any(report["issues"] for report in reports) else 0
        reports = []
        while True:
            report = parse_batch(args.project, limit=args.limit, max_bytes=args.max_mb * 1024 * 1024,
                                 max_wall_seconds=args.max_wall_seconds)
            reports.append(report)
            print(json.dumps(report, sort_keys=True), flush=True)
            if not args.all or report["selected"] == 0 or report["errors"]:
                break
        return 1 if any(report["errors"] for report in reports) else 0
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
