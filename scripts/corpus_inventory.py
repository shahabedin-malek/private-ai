#!/usr/bin/env python3
"""Build a deterministic inventory of the immutable Private AI repository corpus.

This phase reads and hashes files only. It never extracts, imports, or executes corpus content.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import contextmanager
import hashlib
import io
import json
import mimetypes
import os
import re
import sqlite3
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
ARCHIVE_EXTENSIONS = {
    ".zip", ".gz", ".tgz", ".tar", ".bz2", ".xz", ".7z", ".rar", ".deb", ".rpm",
    ".vsix", ".apk", ".jar", ".war", ".egg", ".whl", ".iso", ".cpio", ".ar", ".cab",
    ".zst", ".pkg", ".dmg", ".msi",
}
PACKAGE_TYPES = {
    ".deb": "debian-package", ".rpm": "rpm-package", ".vsix": "vscode-extension",
    ".whl": "python-wheel", ".egg": "python-egg", ".apk": "android-package",
    ".appimage": "appimage", ".jar": "java-archive", ".war": "java-web-archive",
    ".zip": "zip-archive", ".tar": "tar-archive", ".tgz": "tar-gzip-archive",
    ".7z": "7zip-archive", ".rar": "rar-archive", ".iso": "iso-image",
}

GLOBAL_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS repositories (
 repository_id TEXT PRIMARY KEY, name TEXT NOT NULL, original_path TEXT NOT NULL,
 workspace_path TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
 discovered_at TEXT NOT NULL, updated_at TEXT NOT NULL, item_size INTEGER NOT NULL DEFAULT 0,
 item_sha256 TEXT, file_count INTEGER NOT NULL DEFAULT 0, directory_count INTEGER NOT NULL DEFAULT 0,
 UNIQUE(original_path)
);
CREATE TABLE IF NOT EXISTS repository_files (
 file_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL REFERENCES repositories(repository_id),
 original_path TEXT NOT NULL, relative_path TEXT NOT NULL, filename TEXT NOT NULL,
 extension TEXT NOT NULL, size_bytes INTEGER NOT NULL, sha256 TEXT, mime_type TEXT NOT NULL,
 detected_format TEXT NOT NULL, executable INTEGER NOT NULL, archive_status TEXT NOT NULL,
 package_type TEXT NOT NULL, node_type TEXT NOT NULL, discovery_timestamp TEXT NOT NULL,
 status TEXT NOT NULL, UNIQUE(repository_id, relative_path)
);
CREATE INDEX IF NOT EXISTS idx_repository_files_hash ON repository_files(sha256);
CREATE INDEX IF NOT EXISTS idx_repository_files_mime ON repository_files(mime_type);
CREATE INDEX IF NOT EXISTS idx_repository_files_repo ON repository_files(repository_id);
CREATE TABLE IF NOT EXISTS processing_runs (
 run_id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT NOT NULL, started_at TEXT NOT NULL,
 ended_at TEXT, status TEXT NOT NULL, details_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processing_errors (
 error_id INTEGER PRIMARY KEY AUTOINCREMENT, repository_id TEXT, file_path TEXT,
 phase TEXT NOT NULL, error TEXT NOT NULL, tool TEXT NOT NULL, tool_version TEXT NOT NULL,
 timestamp TEXT NOT NULL, retry_count INTEGER NOT NULL DEFAULT 0, next_action TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS file_hashes (
 repository_id TEXT NOT NULL, relative_path TEXT NOT NULL, sha256 TEXT NOT NULL,
 size_bytes INTEGER NOT NULL, PRIMARY KEY(repository_id, relative_path)
);
"""

GLOBAL_ENTITY_TABLES = (
    "directories", "archives", "extracted_files", "file_metadata", "text_content", "code_entities",
    "code_symbols", "imports", "dependencies", "packages", "executables", "urls", "domains",
    "organizations", "people", "products", "projects", "technologies", "frameworks", "models",
    "apis", "services", "commands", "features", "capabilities", "categories", "tags",
    "knowledge_documents", "research_sources", "research_claims", "relationships", "duplicates",
    "similar_files", "memory_records", "conversation_records", "task_records", "tool_registry",
    "model_registry", "provider_registry", "token_usage", "search_events", "research_events", "audit_log",
)


def extend_global_schema(con: sqlite3.Connection) -> None:
    for table in GLOBAL_ENTITY_TABLES:
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {table} (record_id TEXT PRIMARY KEY, "
            "repository_id TEXT REFERENCES repositories(repository_id), "
            "file_id TEXT REFERENCES repository_files(file_id), entity_key TEXT NOT NULL, "
            "payload_json TEXT NOT NULL DEFAULT '{}', source_path TEXT, confidence TEXT, "
            "created_at TEXT NOT NULL DEFAULT '')"
        )
        con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_repository ON {table}(repository_id)")
        con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_file ON {table}(file_id)")
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(record_id UNINDEXED, content, tokenize='unicode61')")
    except sqlite3.OperationalError:
        con.execute("CREATE TABLE IF NOT EXISTS knowledge_fts(record_id TEXT PRIMARY KEY, content TEXT NOT NULL)")


REPO_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS repository (
 repository_id TEXT PRIMARY KEY, name TEXT NOT NULL, original_path TEXT NOT NULL,
 discovered_at TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
 file_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL REFERENCES repository(repository_id),
 original_path TEXT NOT NULL, relative_path TEXT NOT NULL, filename TEXT NOT NULL,
 extension TEXT NOT NULL, size_bytes INTEGER NOT NULL, sha256 TEXT, mime_type TEXT NOT NULL,
 detected_format TEXT NOT NULL, executable INTEGER NOT NULL, archive_status TEXT NOT NULL,
 package_type TEXT NOT NULL, node_type TEXT NOT NULL, status TEXT NOT NULL,
 UNIQUE(repository_id, relative_path)
);
CREATE TABLE IF NOT EXISTS file_hashes (
 file_id TEXT PRIMARY KEY REFERENCES files(file_id), sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS directories (
 repository_id TEXT NOT NULL REFERENCES repository(repository_id), relative_path TEXT NOT NULL,
 PRIMARY KEY(repository_id, relative_path)
);
CREATE TABLE IF NOT EXISTS archives (
 file_id TEXT PRIMARY KEY REFERENCES files(file_id), detected_format TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'DISCOVERED'
);
CREATE TABLE IF NOT EXISTS extractions (
 extraction_id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT NOT NULL REFERENCES files(file_id),
 status TEXT NOT NULL, destination TEXT, tool TEXT, tool_version TEXT, timestamp TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS metadata (file_id TEXT NOT NULL REFERENCES files(file_id), key TEXT NOT NULL,
 value_json TEXT NOT NULL, PRIMARY KEY(file_id, key));
CREATE TABLE IF NOT EXISTS text_content (file_id TEXT PRIMARY KEY REFERENCES files(file_id),
 canonical_path TEXT, sha256 TEXT, byte_length INTEGER, status TEXT NOT NULL DEFAULT 'PENDING');
CREATE TABLE IF NOT EXISTS provenance (record_id TEXT PRIMARY KEY, file_id TEXT REFERENCES files(file_id),
 tool TEXT NOT NULL, tool_version TEXT NOT NULL, pipeline TEXT NOT NULL, timestamp TEXT NOT NULL,
 source_path TEXT NOT NULL, source_sha256 TEXT, details_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS code_symbols (symbol_id INTEGER PRIMARY KEY, file_id TEXT NOT NULL REFERENCES files(file_id),
 name TEXT NOT NULL, kind TEXT NOT NULL, line INTEGER);
CREATE TABLE IF NOT EXISTS imports (file_id TEXT NOT NULL REFERENCES files(file_id), target TEXT NOT NULL,
 PRIMARY KEY(file_id, target));
CREATE TABLE IF NOT EXISTS dependencies (file_id TEXT NOT NULL REFERENCES files(file_id), name TEXT NOT NULL,
 version TEXT, source TEXT, PRIMARY KEY(file_id, name, version));
CREATE TABLE IF NOT EXISTS urls (file_id TEXT NOT NULL REFERENCES files(file_id), url TEXT NOT NULL,
 PRIMARY KEY(file_id, url));
CREATE TABLE IF NOT EXISTS entities (file_id TEXT NOT NULL REFERENCES files(file_id), name TEXT NOT NULL,
 kind TEXT NOT NULL, confidence TEXT NOT NULL, PRIMARY KEY(file_id, name, kind));
CREATE TABLE IF NOT EXISTS technologies (file_id TEXT NOT NULL REFERENCES files(file_id), name TEXT NOT NULL,
 PRIMARY KEY(file_id, name));
CREATE TABLE IF NOT EXISTS features (file_id TEXT NOT NULL REFERENCES files(file_id), name TEXT NOT NULL,
 evidence TEXT, PRIMARY KEY(file_id, name));
CREATE TABLE IF NOT EXISTS commands (file_id TEXT NOT NULL REFERENCES files(file_id), command TEXT NOT NULL,
 PRIMARY KEY(file_id, command));
CREATE TABLE IF NOT EXISTS packages (file_id TEXT PRIMARY KEY REFERENCES files(file_id), package_type TEXT NOT NULL,
 metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS relationships (source_file_id TEXT NOT NULL REFERENCES files(file_id),
 target TEXT NOT NULL, relationship TEXT NOT NULL, PRIMARY KEY(source_file_id, target, relationship));
CREATE TABLE IF NOT EXISTS research_sources (source_id TEXT PRIMARY KEY, file_id TEXT REFERENCES files(file_id),
 source TEXT NOT NULL, source_path TEXT, imported_at TEXT NOT NULL, provenance_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS research_claims (claim_id TEXT PRIMARY KEY, file_id TEXT REFERENCES files(file_id),
 claim TEXT NOT NULL, evidence TEXT NOT NULL, confidence TEXT NOT NULL, provenance_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS provenance (record_id TEXT PRIMARY KEY, file_id TEXT REFERENCES files(file_id),
 tool TEXT NOT NULL, tool_version TEXT NOT NULL, pipeline TEXT NOT NULL, timestamp TEXT NOT NULL,
 source_path TEXT NOT NULL, source_sha256 TEXT, details_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS processing_runs (run_id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT NOT NULL,
 started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL, details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS processing_errors (error_id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT,
 phase TEXT NOT NULL, error TEXT NOT NULL, tool TEXT NOT NULL, tool_version TEXT NOT NULL,
 timestamp TEXT NOT NULL, retry_count INTEGER NOT NULL DEFAULT 0, next_action TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_mime ON files(mime_type);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def stable_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._").lower()
    return slug[:64] or "unnamed"


def source_stat(path: Path) -> dict[str, int]:
    st = path.lstat()
    return {"device": st.st_dev, "inode": st.st_ino, "mode": st.st_mode,
            "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def digest_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise OSError("file changed type during inventory")
        while block := stream.read(1024 * 1024):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def sniff_format(path: Path, extension: str, mime: str) -> tuple[str, bool, str]:
    try:
        with path.open("rb") as stream:
            head = stream.read(512)
    except OSError:
        return "unreadable", extension in ARCHIVE_EXTENSIONS, "application/octet-stream"
    signatures = (
        (b"PK\x03\x04", "zip"), (b"PK\x05\x06", "zip"), (b"PK\x07\x08", "zip"),
        (b"\x1f\x8b", "gzip"), (b"BZh", "bzip2"), (b"\xfd7zXZ\x00", "xz"),
        (b"7z\xbc\xaf\x27\x1c", "7z"), (b"Rar!\x1a\x07", "rar"),
        (b"\x28\xb5\x2f\xfd", "zstd"), (b"!<arch>\n", "ar"),
        (b"\x7fELF", "elf"), (b"MZ", "pe-executable"),
        (b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpeg"), (b"%PDF-", "pdf"),
    )
    for signature, name in signatures:
        if head.startswith(signature):
            detected_mime = {"zip": "application/zip", "gzip": "application/gzip", "bzip2": "application/x-bzip2", "xz": "application/x-xz", "7z": "application/x-7z-compressed", "rar": "application/vnd.rar", "zstd": "application/zstd", "ar": "application/x-archive", "elf": "application/x-elf", "pe-executable": "application/vnd.microsoft.portable-executable", "png": "image/png", "jpeg": "image/jpeg", "pdf": "application/pdf"}.get(name, mime)
            return name, name in {"zip", "gzip", "bzip2", "xz", "7z", "rar", "zstd", "ar"} or extension in ARCHIVE_EXTENSIONS, detected_mime
    if len(head) >= 265 and head[257:262] == b"ustar":
        return "tar", True, "application/x-tar"
    if mime.startswith("text/") or extension in {".py", ".js", ".ts", ".md", ".json", ".toml", ".yaml", ".yml", ".xml", ".html", ".css", ".sql", ".sh", ".rs", ".go", ".java"}:
        return "text", extension in ARCHIVE_EXTENSIONS, "text/plain"
    return extension.lstrip(".") or "binary", extension in ARCHIVE_EXTENSIONS, mime


def kind_for(name: str, is_dir: bool) -> str:
    if is_dir:
        return "directory"
    ext = Path(name).suffix.lower()
    return PACKAGE_TYPES.get(ext, "archive" if ext in ARCHIVE_EXTENSIONS else "file")


def walk_item(path: Path, corpus: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files: list[dict[str, Any]] = []
    directories: list[dict[str, Any]] = []
    base_stat = path.lstat()
    if stat.S_ISDIR(base_stat.st_mode):
        for current, dirnames, filenames in os.walk(path, followlinks=False):
            current_path = Path(current)
            dirnames.sort()
            filenames.sort()
            for dirname in list(dirnames):
                child = current_path / dirname
                rel = child.relative_to(path).as_posix()
                child_stat = child.lstat()
                values = {"device": child_stat.st_dev, "inode": child_stat.st_ino, "mode": child_stat.st_mode,
                          "size": child_stat.st_size, "mtime_ns": child_stat.st_mtime_ns}
                if stat.S_ISLNK(child_stat.st_mode):
                    dirnames.remove(dirname)
                    files.append(describe(child, path, corpus))
                else:
                    directories.append({"relative_path": rel, "source_stat": values})
            for filename in filenames:
                files.append(describe(current_path / filename, path, corpus))
    else:
        files.append(describe(path, path.parent, corpus))
    return files, directories


def describe(path: Path, item_root: Path, corpus: Path) -> dict[str, Any]:
    st = path.lstat()
    stat_record = {"device": st.st_dev, "inode": st.st_ino, "mode": st.st_mode,
                   "size": st.st_size, "mtime_ns": st.st_mtime_ns}
    rel = path.relative_to(item_root).as_posix()
    original = path.relative_to(corpus).as_posix()
    extension = path.suffix.lower()
    mime_guess = mimetypes.guess_type(path.name, strict=False)[0] or "application/octet-stream"
    if stat.S_ISLNK(st.st_mode):
        return {"original_path": original, "relative_path": rel, "filename": path.name,
                "extension": extension, "size_bytes": st.st_size, "sha256": None,
                "mime_type": "inode/symlink", "detected_format": "symlink-not-followed", "source_stat": stat_record,
                "executable": False, "archive_status": "not-expanded", "package_type": kind_for(path.name, False),
                "node_type": "symlink", "status": "DISCOVERED"}
    if not stat.S_ISREG(st.st_mode):
        return {"original_path": original, "relative_path": rel, "filename": path.name,
                "extension": extension, "size_bytes": st.st_size, "sha256": None,
                "mime_type": "application/octet-stream", "detected_format": "special-file-not-read", "source_stat": stat_record,
                "executable": False, "archive_status": "not-expanded", "package_type": kind_for(path.name, False),
                "node_type": "special", "status": "BLOCKED"}
    sha256, size = digest_file(path)
    after = path.lstat()
    if (st.st_ino, st.st_size, st.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns) or size != st.st_size:
        raise OSError("file changed while hashing; retry inventory")
    detected, archive, detected_mime = sniff_format(path, extension, mime_guess)
    return {"original_path": original, "relative_path": rel, "filename": path.name,
            "extension": extension, "size_bytes": size, "sha256": sha256,
            "mime_type": detected_mime, "extension": extension, "detected_format": detected, "source_stat": stat_record,
            "executable": bool(st.st_mode & 0o111),
            "archive_status": "candidate-not-expanded" if archive else "not-archive",
            "package_type": kind_for(path.name, False), "node_type": "file", "status": "DISCOVERED"}


def cache_valid(path: Path, cached: dict[str, Any]) -> bool:
    """Accept checkpointed hashes only when the complete lstat tree is unchanged."""
    expected_files = {x["relative_path"]: x.get("source_stat") for x in cached.get("files", [])}
    expected_dirs = {x["relative_path"]: x.get("source_stat") for x in cached.get("directories", [])}
    if not all(expected_files.values()) or not all(expected_dirs.values()):
        return False
    actual_files: dict[str, dict[str, int]] = {}
    actual_dirs: dict[str, dict[str, int]] = {}
    try:
        top = path.lstat()
        if not stat.S_ISDIR(top.st_mode):
            rel = path.name if path.parent == path else cached.get("item", {}).get("original_path", path.name)
            rel = Path(rel).name
            return expected_files == {rel: {"device": top.st_dev, "inode": top.st_ino,
                "mode": top.st_mode, "size": top.st_size, "mtime_ns": top.st_mtime_ns}} and not expected_dirs
        for current, dirnames, filenames in os.walk(path, followlinks=False):
            current_path = Path(current)
            for dirname in list(dirnames):
                child = current_path / dirname
                rel = child.relative_to(path).as_posix()
                child_st = child.lstat()
                values = {"device": child_st.st_dev, "inode": child_st.st_ino, "mode": child_st.st_mode,
                          "size": child_st.st_size, "mtime_ns": child_st.st_mtime_ns}
                if stat.S_ISLNK(child_st.st_mode):
                    actual_files[rel] = values
                    dirnames.remove(dirname)
                else:
                    actual_dirs[rel] = values
            for filename in filenames:
                child = current_path / filename
                child_st = child.lstat()
                actual_files[child.relative_to(path).as_posix()] = {
                    "device": child_st.st_dev, "inode": child_st.st_ino, "mode": child_st.st_mode,
                    "size": child_st.st_size, "mtime_ns": child_st.st_mtime_ns}
    except OSError:
        return False
    return expected_files == actual_files and expected_dirs == actual_dirs


def read_prior(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"repositories": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read existing manifest safely: {exc}")


def assign_ids(items: list[dict[str, Any]], previous: dict[str, Any]) -> None:
    old = previous.get("repositories", [])
    by_path = {x.get("original_path"): x.get("repository_id") for x in old if x.get("repository_id")}
    by_inode = {(x.get("device"), x.get("inode")): x.get("repository_id") for x in old
                if x.get("device") is not None and x.get("inode") is not None and x.get("repository_id")}
    used = {v for v in by_path.values() if v}
    used.update(v for v in by_inode.values() if v)
    next_number = max((int(x[5:]) for x in used if re.fullmatch(r"REPO-\d{4,}", x)), default=0) + 1
    for item in items:
        prior_id = by_path.get(item["original_path"]) or by_inode.get((item.get("device"), item.get("inode")))
        if prior_id:
            item["repository_id"] = prior_id
        else:
            while f"REPO-{next_number:04d}" in used:
                next_number += 1
            item["repository_id"] = f"REPO-{next_number:04d}"
            used.add(item["repository_id"])
            next_number += 1


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    try:
        with con:
            yield con
    finally:
        con.close()


def insert_repo_db(item: dict[str, Any], files: list[dict[str, Any]], directories: list[dict[str, Any]], db: Path) -> None:
    with connect(db) as con:
        con.executescript(REPO_SCHEMA)
        con.execute("INSERT INTO repository VALUES(?,?,?,?,?) ON CONFLICT(repository_id) DO UPDATE SET name=excluded.name,original_path=excluded.original_path,discovered_at=excluded.discovered_at,status=excluded.status",
                    (item["repository_id"], item["name"], item["original_path"], item["discovered_at"], "DISCOVERED"))
        con.execute("DELETE FROM directories WHERE repository_id=?", (item["repository_id"],))
        con.execute("UPDATE files SET status='MISSING' WHERE repository_id=?", (item["repository_id"],))
        for directory in directories:
            con.execute("INSERT INTO directories VALUES(?,?) ON CONFLICT(repository_id,relative_path) DO NOTHING",
                        (item["repository_id"], directory["relative_path"]))

        for f in files:
            file_id = f"{item['repository_id']}:{hashlib.sha256(f['relative_path'].encode()).hexdigest()[:20]}"
            con.execute("""INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(file_id) DO UPDATE SET original_path=excluded.original_path,
                relative_path=excluded.relative_path,filename=excluded.filename,extension=excluded.extension,
                size_bytes=excluded.size_bytes,sha256=excluded.sha256,mime_type=excluded.mime_type,
                detected_format=excluded.detected_format,executable=excluded.executable,
                archive_status=excluded.archive_status,package_type=excluded.package_type,
                node_type=excluded.node_type,status=excluded.status""", (
                file_id, item["repository_id"], f["original_path"], f["relative_path"], f["filename"],
                f["extension"], f["size_bytes"], f["sha256"], f["mime_type"], f["detected_format"],
                int(f["executable"]), f["archive_status"], f["package_type"], f["node_type"], f["status"]))
            if f["sha256"]:
                con.execute("INSERT INTO file_hashes VALUES(?,?,?) ON CONFLICT(file_id) DO UPDATE SET sha256=excluded.sha256,size_bytes=excluded.size_bytes",
                            (file_id, f["sha256"], f["size_bytes"]))
                con.execute("INSERT INTO text_content(file_id,canonical_path,sha256,byte_length,status) VALUES(?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET canonical_path=excluded.canonical_path,sha256=excluded.sha256,byte_length=excluded.byte_length,status=CASE WHEN text_content.sha256=excluded.sha256 THEN text_content.status ELSE 'PENDING' END",
                            (file_id, None, f["sha256"], f["size_bytes"], "PENDING"))
                con.execute("INSERT INTO metadata VALUES(?,?,?) ON CONFLICT(file_id,key) DO UPDATE SET value_json=excluded.value_json",
                            (file_id, "inventory", json.dumps({k: f[k] for k in ("mime_type", "detected_format", "extension", "executable", "archive_status", "package_type", "source_stat")}, sort_keys=True)))
                con.execute("INSERT INTO provenance VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET tool_version=excluded.tool_version,timestamp=excluded.timestamp,source_sha256=excluded.source_sha256,details_json=excluded.details_json",
                            (file_id, file_id, "corpus_inventory.py", str(SCHEMA_VERSION), "inventory-v1", item["updated_at"], f["original_path"], f["sha256"], json.dumps({"root": item["original_path"]}, sort_keys=True)))
            if f["archive_status"] == "candidate-not-expanded":
                con.execute("INSERT INTO archives VALUES(?,?,?) ON CONFLICT(file_id) DO UPDATE SET detected_format=excluded.detected_format,status=excluded.status",
                            (file_id, f["detected_format"], "DISCOVERED"))
            if f["package_type"] not in {"file", "archive"}:
                con.execute("INSERT INTO packages VALUES(?,?,?) ON CONFLICT(file_id) DO UPDATE SET package_type=excluded.package_type,metadata_json=excluded.metadata_json",
                            (file_id, f["package_type"], json.dumps({"filename": f["filename"], "extension": f["extension"], "format": f["detected_format"]}, sort_keys=True)))
        con.execute("INSERT INTO processing_runs(phase,started_at,ended_at,status,details_json) VALUES(?,?,?,?,?)",
                    ("inventory", item["discovered_at"], item["updated_at"], "COMPLETED",
                     json.dumps({"file_count": len(files), "directory_count": len(directories)}, sort_keys=True)))


def build(root: Path, output: Path, *, offset: int = 0, limit: int = 40) -> dict[str, Any]:
    corpus = root.resolve(strict=True)
    output = output.resolve()
    if not corpus.is_dir():
        raise SystemExit(f"corpus root is not a directory: {corpus}")
    if output == corpus or corpus in output.parents:
        raise SystemExit("output may not be inside the raw corpus")
    if offset < 0 or limit < 1:
        raise SystemExit("offset must be non-negative and limit must be positive")
    manifests = output / "data" / "manifests"
    prior = read_prior(manifests / "REPO_MANIFEST.json")
    old_items = prior.get("repositories", [])
    old_by_path = {x.get("original_path"): x for x in old_items}
    physical_names = sorted(os.listdir(corpus))
    nested_current_paths = {
        item.get("original_path") for item in old_items
        if len(Path(item.get("original_path", "")).parts) > 1
        and (corpus / item.get("original_path", "")).is_file()
    }
    represented_nested_roots = {Path(path).parts[0] for path in nested_current_paths}
    # When individual items under repo/new have stable IDs, do not also inventory
    # their containing directory as an overlapping repository.
    names = [name for name in physical_names if name not in represented_nested_roots]
    timestamp = now()
    batch_names = names[offset:offset + limit]
    checkpoint_dir = manifests / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    for index, name in enumerate(batch_names, start=offset + 1):
        path = corpus / name
        try:
            st = path.lstat()
            old = old_by_path.get(name, {})
            item = {"name": name, "original_path": name, "device": st.st_dev, "inode": st.st_ino,
                    "discovered_at": old.get("discovered_at", timestamp), "updated_at": timestamp,
                    "kind": kind_for(name, stat.S_ISDIR(st.st_mode)), "status": "DISCOVERED",
                    "size_bytes": 0, "sha256": None, "file_count": 0, "directory_count": 0}
            checkpoint_path = checkpoint_dir / (hashlib.sha256(name.encode("utf-8", "surrogateescape")).hexdigest() + ".json")
            checkpoint = None
            if checkpoint_path.exists():
                try:
                    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    checkpoint = None
            if checkpoint and checkpoint.get("name") == name and cache_valid(path, checkpoint):
                files, directories = checkpoint["files"], checkpoint["directories"]
                item.update(checkpoint["item"])
                item["updated_at"] = timestamp
            else:
                files, directories = walk_item(path, corpus)
            item["source_stat"] = source_stat(path)
            item["size_bytes"] = sum(f["size_bytes"] for f in files if f["node_type"] == "file")
            item["file_count"] = sum(f["node_type"] == "file" for f in files)
            item["directory_count"] = len(directories) + int(stat.S_ISDIR(st.st_mode))
            item["sha256"] = hashlib.sha256("\n".join(sorted(f["sha256"] or "" for f in files)).encode()).hexdigest() if files else None
            atomic_write(checkpoint_path, json.dumps({"name": name, "item": item, "files": files,
                          "directories": directories}, ensure_ascii=False, sort_keys=True) + "\n")
            atomic_write(manifests / "INVENTORY_PROGRESS.md",
                         f"# Corpus Inventory Checkpoint\n\nUpdated: {now()}\n\n- Current item: `{name}`\n- Completed batch positions: {index} of {len(names)}\n- This is an intermediate checkpoint; final manifests publish only after all records and databases are written.\n")
        except Exception as exc:
            errors.append({"path": name, "error": f"{type(exc).__name__}: {exc}"})
            error_item = {"name": name, "original_path": name, "device": None, "inode": None,
                          "discovered_at": old_by_path.get(name, {}).get("discovered_at", timestamp),
                          "updated_at": timestamp, "kind": "unknown", "status": "FAILED",
                          "size_bytes": 0, "sha256": None, "file_count": 0, "directory_count": 0,
                          "source_stat": None}
            atomic_write(checkpoint_path, json.dumps({"name": name, "item": error_item,
                          "files": [], "directories": [], "error": errors[-1]["error"]}, sort_keys=True) + "\n")
    checkpoints: dict[str, dict[str, Any]] = {}
    for name in names:
        checkpoint_path = checkpoint_dir / (hashlib.sha256(name.encode("utf-8", "surrogateescape")).hexdigest() + ".json")
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint.get("name") == name and cache_valid(corpus / name, checkpoint):
                checkpoints[name] = checkpoint
        except (OSError, json.JSONDecodeError):
            continue
    if len(checkpoints) != len(names):
        atomic_write(manifests / "INVENTORY_PROGRESS.md",
                     f"# Corpus Inventory Checkpoint\n\nUpdated: {now()}\n\n- Most recent batch: items {offset + 1}–{min(offset + limit, len(names))} of {len(names)}\n- Validated top-level checkpoints: {len(checkpoints)} of {len(names)}\n- Status: IN_PROGRESS\n- Next batch command: `python3 scripts/corpus_inventory.py --root repo --output . --offset {min(offset + limit, len(names))} --limit {limit}`\n")
        return {"totals": {"top_level_items": len(names), "checkpointed_items": len(checkpoints)}, "errors": errors}
    timestamp = now()
    items = []
    files_by_repo: dict[str, list[dict[str, Any]]] = {}
    dirs_by_repo: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        checkpoint = checkpoints[name]
        item = checkpoint["item"]
        items.append(item)
        files_by_repo[name] = checkpoint["files"]
        dirs_by_repo[name] = checkpoint["directories"]
        if checkpoint.get("error"):
            errors.append({"path": name, "error": checkpoint["error"]})
    assign_ids(items, prior)
    current = {x["original_path"] for x in items}
    retired = [{**old, "status": "MISSING", "updated_at": timestamp}
               for old in old_items if old.get("original_path") not in current
               and old.get("original_path") not in nested_current_paths]
    old_files_by_repo: dict[str, list[dict[str, Any]]] = {}
    for record in prior.get("files", []):
        old_files_by_repo.setdefault(record["repository_id"], []).append(record)
    for item in retired:
        name = item["name"]
        files_by_repo[name] = [{**record, "status": "MISSING"}
                               for record in old_files_by_repo.get(item["repository_id"], [])]
        dirs_by_repo[name] = []
    items = sorted(items + retired, key=lambda x: x["repository_id"])
    checkpoint_dir = manifests / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    for index, name in enumerate(batch_names, start=offset + 1):
        path = corpus / name
        try:
            st = path.lstat()
            old = old_by_path.get(name, {})
            item = {"name": name, "original_path": name, "device": st.st_dev, "inode": st.st_ino,
                    "discovered_at": old.get("discovered_at", timestamp), "updated_at": timestamp,
                    "kind": kind_for(name, stat.S_ISDIR(st.st_mode)), "status": "DISCOVERED",
                    "size_bytes": 0, "sha256": None, "file_count": 0, "directory_count": 0}
            checkpoint_path = checkpoint_dir / (hashlib.sha256(name.encode("utf-8", "surrogateescape")).hexdigest() + ".json")
            checkpoint = None
            if checkpoint_path.exists():
                try:
                    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    checkpoint = None
            if checkpoint and checkpoint.get("name") == name and cache_valid(path, checkpoint):
                files, directories = checkpoint["files"], checkpoint["directories"]
                item.update(checkpoint["item"])
                item["updated_at"] = timestamp
            else:
                files, directories = walk_item(path, corpus)
            item["source_stat"] = source_stat(path)
            item["size_bytes"] = sum(f["size_bytes"] for f in files if f["node_type"] == "file")
            item["file_count"] = sum(f["node_type"] == "file" for f in files)
            item["directory_count"] = len(directories) + int(stat.S_ISDIR(st.st_mode))
            item["sha256"] = hashlib.sha256("\n".join(sorted(f["sha256"] or "" for f in files)).encode()).hexdigest() if files else None
            atomic_write(checkpoint_path, json.dumps({"name": name, "item": item, "files": files,
                          "directories": directories}, ensure_ascii=False, sort_keys=True) + "\n")
            atomic_write(manifests / "INVENTORY_PROGRESS.md",
                         f"# Corpus Inventory Checkpoint\n\nUpdated: {now()}\n\n- Current item: `{name}`\n- Completed batch positions: {index} of {len(names)}\n- This is an intermediate checkpoint; final manifests publish only after all records and databases are written.\n")
        except Exception as exc:
            errors.append({"path": name, "error": f"{type(exc).__name__}: {exc}"})
            error_item = {"name": name, "original_path": name, "device": None, "inode": None,
                          "discovered_at": old_by_path.get(name, {}).get("discovered_at", timestamp),
                          "updated_at": timestamp, "kind": "unknown", "status": "FAILED",
                          "size_bytes": 0, "sha256": None, "file_count": 0, "directory_count": 0,
                          "source_stat": None}
            atomic_write(checkpoint_path, json.dumps({"name": name, "item": error_item,
                          "files": [], "directories": [], "error": errors[-1]["error"]}, sort_keys=True) + "\n")
    checkpoints: dict[str, dict[str, Any]] = {}
    for name in names:
        checkpoint_path = checkpoint_dir / (hashlib.sha256(name.encode("utf-8", "surrogateescape")).hexdigest() + ".json")
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if checkpoint.get("name") == name and cache_valid(corpus / name, checkpoint):
                checkpoints[name] = checkpoint
        except (OSError, json.JSONDecodeError):
            continue
    if len(checkpoints) != len(names):
        atomic_write(manifests / "INVENTORY_PROGRESS.md",
                     f"# Corpus Inventory Checkpoint\n\nUpdated: {now()}\n\n- Most recent batch: items {offset + 1}–{min(offset + limit, len(names))} of {len(names)}\n- Validated top-level checkpoints: {len(checkpoints)} of {len(names)}\n- Status: IN_PROGRESS\n- Next batch command: `python3 scripts/corpus_inventory.py --root repo --output . --offset {min(offset + limit, len(names))} --limit {limit}`\n")
        return {"totals": {"top_level_items": len(names), "checkpointed_items": len(checkpoints)}, "errors": errors}
    timestamp = now()
    items = []
    files_by_repo: dict[str, list[dict[str, Any]]] = {}
    dirs_by_repo: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        checkpoint = checkpoints[name]
        item = checkpoint["item"]
        items.append(item)
        files_by_repo[name] = checkpoint["files"]
        dirs_by_repo[name] = checkpoint["directories"]
        if checkpoint.get("error"):
            errors.append({"path": name, "error": checkpoint["error"]})
    assign_ids(items, prior)
    current = {x["original_path"] for x in items}
    retired = [{**old, "status": "MISSING", "updated_at": timestamp}
               for old in old_items if old.get("original_path") not in current
               and old.get("original_path") not in nested_current_paths]
    old_files_by_repo: dict[str, list[dict[str, Any]]] = {}
    for record in prior.get("files", []):
        old_files_by_repo.setdefault(record["repository_id"], []).append(record)
    retired_paths = {item.get("original_path", "") for item in retired}
    additive_items = [
        {**old, "updated_at": timestamp}
        for old in old_items
        if len(Path(old.get("original_path", "")).parts) > 1
        and old.get("original_path") not in retired_paths
        and (corpus / old["original_path"]).is_file()
    ]
    for item in retired + additive_items:
        name = item["name"]
        source_records = old_files_by_repo.get(item["repository_id"], [])
        files_by_repo[name] = ([{**record, "status": "MISSING"} for record in source_records]
                               if item in retired else source_records)
        dirs_by_repo[name] = []
    items = sorted(items + retired + additive_items, key=lambda x: x["repository_id"])
    flat_files: list[dict[str, Any]] = []
    global_db = output / "data" / "database" / "private_ai_corpus.sqlite"
    with connect(global_db) as con:
        con.executescript(GLOBAL_SCHEMA)
        extend_global_schema(con)
        with con:
            for item in items:
                repo_id = item["repository_id"]
                if item["status"] == "MISSING":
                    con.execute("UPDATE repositories SET status='MISSING',updated_at=? WHERE repository_id=?", (timestamp, repo_id))
                    con.execute("UPDATE repository_files SET status='MISSING' WHERE repository_id=?", (repo_id,))
                    con.execute("UPDATE text_content SET payload_json=json_set(payload_json,'$.status','MISSING') WHERE repository_id=?", (repo_id,))
                    con.execute("UPDATE archives SET payload_json=json_set(payload_json,'$.status','MISSING') WHERE repository_id=?", (repo_id,))
                    workspace_name = f"{repo_id}-{stable_slug(item['name'])}"
                    repository_db = output / "data" / "repos" / workspace_name / "db" / f"{stable_slug(item['name'])}.sqlite"
                    if repository_db.is_file():
                        with connect(repository_db) as repo_con:
                            repo_con.execute("UPDATE repository SET status='MISSING' WHERE repository_id=?", (repo_id,))
                            repo_con.execute("UPDATE files SET status='MISSING' WHERE repository_id=?", (repo_id,))
                            repo_con.execute("UPDATE text_content SET status='MISSING' WHERE file_id IN (SELECT file_id FROM files WHERE repository_id=?)", (repo_id,))
                            repo_con.execute("UPDATE archives SET status='MISSING' WHERE file_id IN (SELECT file_id FROM files WHERE repository_id=?)", (repo_id,))
                    for file in files_by_repo.get(item["name"], []):
                        flat_files.append({**file, "repository_id": repo_id,
                                           "discovery_timestamp": item["discovered_at"]})
                    continue
                name = item["name"]
                workspace_name = f"{repo_id}-{stable_slug(name)}"
                workspace = output / "data" / "repos" / workspace_name
                for folder in ("source", "extracted", "scraped", "db", "logs", "manifest", "research", "derived"):
                    (workspace / folder).mkdir(parents=True, exist_ok=True)
                db_path = workspace / "db" / f"{stable_slug(name)}.sqlite"
                files = files_by_repo.get(name, [])
                directories = dirs_by_repo.get(name, [])
                repo_item = {**item, "workspace_path": str(workspace.relative_to(output))}
                insert_repo_db(repo_item, files, directories, db_path)
                source_path = corpus / item["original_path"]
                atomic_write(workspace / "source" / "README.md",
                             f"# Source reference\n\nRaw corpus material is preserved at `{source_path}`. This directory intentionally holds no mutable copy of the source.\n")
                atomic_write(workspace / "manifest" / "repo.json", json.dumps(
                    {"repository": repo_item, "files": files, "directories": directories},
                    indent=2, ensure_ascii=False, sort_keys=True) + "\n")
                con.execute("INSERT INTO repositories VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(repository_id) DO UPDATE SET name=excluded.name,original_path=excluded.original_path,workspace_path=excluded.workspace_path,kind=excluded.kind,status=excluded.status,updated_at=excluded.updated_at,item_size=excluded.item_size,item_sha256=excluded.item_sha256,file_count=excluded.file_count,directory_count=excluded.directory_count",
                            (repo_id, name, item["original_path"], workspace_name, item["kind"], item["status"],
                             item["discovered_at"], timestamp, item["size_bytes"], item["sha256"], item["file_count"], item["directory_count"]))
                con.execute("UPDATE repository_files SET status='MISSING' WHERE repository_id=?", (repo_id,))
                for f in files:
                    file_id = f"{repo_id}:{hashlib.sha256(f['relative_path'].encode()).hexdigest()[:20]}"
                    record = {**f, "repository_id": repo_id, "file_id": file_id,
                              "discovery_timestamp": item["discovered_at"]}
                    flat_files.append(record)
                    con.execute("""INSERT INTO repository_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(file_id) DO UPDATE SET original_path=excluded.original_path,
                        relative_path=excluded.relative_path,filename=excluded.filename,extension=excluded.extension,
                        size_bytes=excluded.size_bytes,sha256=excluded.sha256,mime_type=excluded.mime_type,
                        detected_format=excluded.detected_format,executable=excluded.executable,
                        archive_status=excluded.archive_status,package_type=excluded.package_type,
                        node_type=excluded.node_type,discovery_timestamp=excluded.discovery_timestamp,status=excluded.status""",
                        (file_id, repo_id, f["original_path"], f["relative_path"], f["filename"], f["extension"],
                         f["size_bytes"], f["sha256"], f["mime_type"], f["detected_format"], int(f["executable"]),
                         f["archive_status"], f["package_type"], f["node_type"], item["discovered_at"], f["status"]))
                    if f["sha256"]:
                        con.execute("INSERT INTO file_hashes VALUES(?,?,?,?) ON CONFLICT(repository_id,relative_path) DO UPDATE SET sha256=excluded.sha256,size_bytes=excluded.size_bytes",
                                    (repo_id, f["relative_path"], f["sha256"], f["size_bytes"]))
                        con.execute("INSERT OR REPLACE INTO text_content(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                    (hashlib.sha256(f"text_content:{repo_id}:{f['relative_path']}".encode()).hexdigest(), repo_id, file_id, f["relative_path"], json.dumps({"sha256": f["sha256"], "size_bytes": f["size_bytes"], "status": "PENDING_PARSE"}, sort_keys=True), f["original_path"], "HIGH", timestamp))
                        con.execute("INSERT OR REPLACE INTO file_metadata(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                    (hashlib.sha256(f"file_metadata:{repo_id}:{f['relative_path']}".encode()).hexdigest(), repo_id, file_id, f["relative_path"], json.dumps({k: f[k] for k in ("mime_type", "detected_format", "extension", "executable", "archive_status", "package_type", "source_stat")}, sort_keys=True), f["original_path"], "HIGH", timestamp))
                        if f["archive_status"] == "candidate-not-expanded":
                            con.execute("INSERT OR REPLACE INTO archives(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                        (hashlib.sha256(f"archives:{repo_id}:{f['relative_path']}".encode()).hexdigest(), repo_id, file_id, f["relative_path"], json.dumps({"format": f["detected_format"], "status": "DISCOVERED"}, sort_keys=True), f["original_path"], "HIGH", timestamp))
                        if f["package_type"] not in {"file", "archive"}:
                            con.execute("INSERT OR REPLACE INTO packages(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                        (hashlib.sha256(f"packages:{repo_id}:{f['relative_path']}".encode()).hexdigest(), repo_id, file_id, f["relative_path"], json.dumps({"type": f["package_type"], "format": f["detected_format"]}, sort_keys=True), f["original_path"], "HIGH", timestamp))
                    if f["detected_format"] in {"elf", "pe-executable"} or f["executable"]:
                        con.execute("INSERT OR REPLACE INTO executables(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                    (hashlib.sha256(f"executables:{repo_id}:{f['relative_path']}".encode()).hexdigest(), repo_id, file_id, f["relative_path"], json.dumps({"format": f["detected_format"], "executable_bit": f["executable"]}, sort_keys=True), f["original_path"], "HIGH", timestamp))
            for directory in dirs_by_repo.get(name, []):
                rel = directory["relative_path"]
                record_id = hashlib.sha256(f"directories:{repo_id}:{rel}".encode()).hexdigest()
                con.execute("INSERT OR REPLACE INTO directories(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                            (record_id, repo_id, None, rel, json.dumps(directory, sort_keys=True), f"{name}/{rel}", "HIGH", timestamp))
        hashes: dict[str, list[dict[str, Any]]] = {}
        for record in flat_files:
            if record.get("sha256"):
                hashes.setdefault(record["sha256"], []).append(record)
        for sha256, duplicates in hashes.items():
            if len(duplicates) < 2:
                continue
            for record in duplicates[1:]:
                key = f"{sha256}:{record['file_id']}"
                record_id = hashlib.sha256(f"duplicates:{key}".encode()).hexdigest()
                con.execute("INSERT OR REPLACE INTO duplicates(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                            (record_id, record["repository_id"], record["file_id"], key,
                             json.dumps({"sha256": sha256, "duplicate_of": duplicates[0]["file_id"]}, sort_keys=True),
                             record["original_path"], "HIGH", timestamp))
        with con:
            for error in errors:
                con.execute("INSERT INTO processing_errors(file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?)",
                            (error["path"], "inventory", error["error"], "corpus_inventory.py", str(SCHEMA_VERSION), timestamp, 0, "retry inventory; inspect path metadata"))
            con.execute("INSERT INTO processing_runs(phase,started_at,ended_at,status,details_json) VALUES(?,?,?,?,?)",
                        ("inventory", timestamp, now(), "COMPLETED" if not errors else "PARTIAL",
                         json.dumps({"items": len(current), "files": len(flat_files), "errors": len(errors)}, sort_keys=True)))
    physical_top_level_items = len(physical_names)
    active_items = [item for item in items if item.get("status") != "MISSING"]
    represented_top_level_paths = {Path(item.get("original_path", "")).parts[0] for item in active_items}
    unrepresented_roots = set(physical_names) - represented_top_level_paths
    payload = {"schema_version": SCHEMA_VERSION, "project": "Private AI", "corpus_root": str(corpus),
               "discovery_timestamp": timestamp,
               "totals": {"top_level_items": len(active_items),
                          "physical_top_level_entries": physical_top_level_items,
                          "unrepresented_top_level_entries": sorted(unrepresented_roots),
                          "regular_files": sum(x["node_type"] == "file" and x["status"] != "MISSING" for x in flat_files),
                          "symlinks": sum(x["node_type"] == "symlink" and x["status"] != "MISSING" for x in flat_files),
                          "directories_below_items": sum(len(dirs_by_repo.get(item["name"], [])) +
                                                           int(item.get("kind") == "directory")
                                                           for item in active_items),
                          "bytes": sum(f["size_bytes"] for f in flat_files if f["status"] != "MISSING"), "failed_items": len(errors),
                          "missing_prior_items": len(retired)},
               "repositories": items, "files": flat_files, "errors": errors}
    manifests.mkdir(parents=True, exist_ok=True)
    atomic_write(manifests / "REPO_MANIFEST.json", json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    output_csv = io.StringIO(newline="")
    fields = ["repository_id", "repository_name", "original_path", "relative_path", "filename", "size_bytes",
              "sha256", "mime_type", "detected_format", "extension", "executable", "archive_status",
              "package_type", "discovery_timestamp", "node_type", "status"]
    writer = csv.DictWriter(output_csv, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    repo_names = {x["repository_id"]: x["name"] for x in items}
    for f in flat_files:
        writer.writerow({**f, "repository_name": repo_names[f["repository_id"]]})
    atomic_write(manifests / "REPO_MANIFEST.csv", output_csv.getvalue())
    totals = payload["totals"]
    summary = ["# Repository Corpus Inventory", "", f"Generated: {timestamp}",
               f"Raw source (read-only): `{corpus}`", "", "## Counts", "",
               f"- Top-level items: **{totals['top_level_items']}**",
               f"- Regular files: **{totals['regular_files']}**",
               f"- Symlinks recorded without following: **{totals['symlinks']}**",
               f"- Nested directories: **{totals['directories_below_items']}**",
               f"- Total bytes hashed: **{totals['bytes']}**",
               f"- Failed items: **{totals['failed_items']}**",
               f"- Prior items now missing: **{totals['missing_prior_items']}**", "",
               "## Stable IDs", "",
               "IDs are assigned in deterministic sorted order on first discovery and retained by original path or filesystem identity. Missing items remain represented; IDs are never recycled.", "",
               "## Errors", ""]
    summary += [f"- `{e['path']}` — {e['error']}" for e in errors] or ["- None recorded."]
    summary += ["", "See `REPO_MANIFEST.json` and `REPO_MANIFEST.csv`. Inventory hashes source bytes, identifies file signatures where recognized and records archive candidates. It does not extract archives or execute source content.", ""]
    atomic_write(manifests / "REPO_INVENTORY.md", "\n".join(summary))
    atomic_write(manifests / "INVENTORY_PROGRESS.md",
                 f"# Corpus Inventory Checkpoint\n\nUpdated: {timestamp}\n\n- Physical top-level entries: {physical_top_level_items}\n- Active stable repository/package items: {totals['top_level_items']}\n- Regular files: {totals['regular_files']}\n- Source bytes: {totals['bytes']}\n- Errors: {totals['failed_items']}\n- Unrepresented top-level entries: {len(unrepresented_roots)}\n- Status: {'VERIFIED' if not errors and not unrepresented_roots else 'PARTIAL'}\n- Next: reconcile manifest IDs, file hashes, global/per-item databases and extraction queue.\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("repo"), help="read-only raw corpus directory")
    parser.add_argument("--output", type=Path, default=Path("."), help="project workspace for generated data")
    parser.add_argument("--offset", type=int, default=0, help="first sorted top-level corpus item in this checkpoint batch")
    parser.add_argument("--limit", type=int, default=40, help="maximum top-level items to hash/checkpoint this run")
    args = parser.parse_args()
    try:
        result = build(args.root, args.output, offset=args.offset, limit=args.limit)
    except Exception as exc:
        print(f"inventory failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result["totals"], sort_keys=True))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
