#!/usr/bin/env python3
"""Audit archive extraction provenance without extracting or modifying corpus sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .corpus_extract import (
        _inventory_file_id, _repository_db_path, _safe_source, _ensure_repo_job_schema,
        _ensure_repo_schema, connect, sha256_file,
    )
except ImportError:  # direct script execution places scripts/ on sys.path
    from corpus_extract import (
        _inventory_file_id, _repository_db_path, _safe_source, _ensure_repo_job_schema,
        _ensure_repo_schema, connect, sha256_file,
    )

OUTPUT_COLUMNS = (
    "extracted_file_id", "member_path", "extracted_path", "parent_archive", "depth",
    "size_bytes", "sha256", "detected_format", "status",
)


def _repository_db_for_source(project: Path, manifest: dict[str, Any], repo_id: str, file_id: str) -> Path:
    try:
        return _repository_db_path(project, manifest, repo_id)
    except FileNotFoundError as initial:
        repository = next(item for item in manifest["repositories"] if item["repository_id"] == repo_id)
        workspace_value = repository.get("workspace_path")
        if not workspace_value:
            with connect(project / "data/database/private_ai_corpus.sqlite") as global_con:
                stored = global_con.execute("SELECT workspace_path FROM repositories WHERE repository_id=?", (repo_id,)).fetchone()
            if stored is None:
                raise FileNotFoundError(f"global repository workspace is missing for {repo_id}") from initial
            workspace_value = str(Path("data") / "repos" / stored["workspace_path"])
        workspace_rel = Path(workspace_value)
        if workspace_rel.is_absolute() or ".." in workspace_rel.parts:
            raise ValueError("per-item workspace path is unsafe")
        workspace = (project / workspace_rel).resolve(strict=True)
        workspace.relative_to(project)
        candidates = sorted((workspace / "db").glob("*.sqlite"))
        matching = []
        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                with connect(candidate) as con:
                    tables = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    source_table = "files" if "files" in tables else "repository_files" if "repository_files" in tables else None
                    if source_table and con.execute(f"SELECT 1 FROM {source_table} WHERE file_id=?", (file_id,)).fetchone():
                        matching.append(candidate)
            except sqlite3.Error:
                continue
        if len(matching) != 1:
            raise FileNotFoundError(f"expected exactly one source-matching database for {repo_id}; found {len(matching)}") from initial
        return matching[0]


def _digest_tree_members(root: Path) -> tuple[str, int, dict[str, tuple[str, int]]]:
    import hashlib

    digest = hashlib.sha256()
    total = 0
    members: dict[str, tuple[str, int]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink found in extraction output: {path}")
        if not path.is_file() or path.relative_to(root).as_posix() in {"extraction.json", ".extraction-journal.jsonl"}:
            continue
        relative = path.relative_to(root).as_posix()
        sha256, size = sha256_file(path)
        encoded = relative.encode()
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(bytes.fromhex(sha256))
        total += size
        members[relative] = (sha256, size)
    return digest.hexdigest(), total, members


def audit(root: Path, project: Path, *, offset: int = 0, limit: int = 25) -> dict[str, Any]:
    corpus = root.resolve(strict=True)
    project = project.resolve(strict=True)
    manifest = json.loads((project / "data/manifests/REPO_MANIFEST.json").read_text(encoding="utf-8"))
    global_db = project / "data/database/private_ai_corpus.sqlite"
    candidates = [row for row in manifest["files"]
                  if row.get("node_type") == "file" and row.get("archive_status") == "candidate-not-expanded"]
    if offset < 0 or limit < 1:
        raise ValueError("offset must be non-negative and limit must be positive")
    batch = candidates[offset:offset + limit]
    issues: list[dict[str, str]] = []
    checked = {"candidates": len(batch), "sources_hashed": 0, "verified_outputs": 0,
               "terminal_jobs": 0, "missing_sources": 0}

    def issue(file_id: str, stage: str, detail: str) -> None:
        issues.append({"file_id": file_id, "stage": stage, "detail": detail})

    with connect(global_db) as global_con:
        job_ids = {row["file_id"] for row in global_con.execute("SELECT file_id FROM extraction_jobs")}
        candidate_ids = {_inventory_file_id(row) for row in candidates}
        for orphan_id in sorted(job_ids - candidate_ids):
            issue(orphan_id, "global-job", "job has no candidate source in the current manifest")
        for row in batch:
            file_id = _inventory_file_id(row)
            repo_id = row["repository_id"]
            expected_path = row["original_path"]
            file_row = global_con.execute("SELECT * FROM repository_files WHERE file_id=?", (file_id,)).fetchone()
            job_row = global_con.execute("SELECT * FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
            global_errors = [dict(r) for r in global_con.execute(
                "SELECT error,next_action,retry_count FROM processing_errors WHERE repository_id=? AND file_path=? AND phase='extraction'",
                (repo_id, expected_path))]
            global_outputs = [dict(r) for r in global_con.execute(
                "SELECT * FROM extraction_outputs WHERE source_file_id=? ORDER BY member_path", (file_id,))]
            if file_row is None:
                issue(file_id, "global-file", "manifest candidate is absent from repository_files")
            elif ((file_row["repository_id"], file_row["original_path"], file_row["sha256"], file_row["size_bytes"])
                  != (repo_id, expected_path, row.get("sha256"), row.get("size_bytes"))):
                issue(file_id, "global-file", "stable ID, source path, size, or hash disagrees with manifest")
            if job_row is None:
                issue(file_id, "global-job", "candidate has no extraction job record")
                continue
            job = dict(job_row)
            source_missing = row.get("status") == "MISSING"
            if ((job["repository_id"], job["source_path"], job["source_sha256"], job["detected_format"])
                != (repo_id, expected_path, row.get("sha256") or "", row.get("detected_format") or "unknown")) and not (
                    source_missing and job["status"] == "FAILED" and "MISSING_SOURCE" in (job.get("error") or "")
                    and (job["repository_id"], job["source_path"], job["source_sha256"])
                    == (repo_id, expected_path, row.get("sha256") or "")):
                issue(file_id, "job-provenance", "source ID/path/hash/format disagrees with manifest")
            try:
                source = _safe_source(corpus, expected_path)
            except FileNotFoundError:
                source = None
            except (OSError, ValueError) as exc:
                source = None
                issue(file_id, "source", f"unsafe or unreadable source path: {type(exc).__name__}: {exc}")
            if source is None:
                if not source_missing:
                    issue(file_id, "source", "source is absent but manifest does not mark it MISSING")
                else:
                    checked["missing_sources"] += 1
                    if job["status"] != "FAILED" or "MISSING_SOURCE" not in (job.get("error") or ""):
                        issue(file_id, "missing-source", "missing input is not explicitly represented by the terminal job error")
            else:
                digest, size = sha256_file(source)
                checked["sources_hashed"] += 1
                if source_missing:
                    issue(file_id, "source", "manifest marks a currently present source as MISSING")
                if (digest, size) != (row.get("sha256"), row.get("size_bytes")):
                    issue(file_id, "source-hash", "current source bytes disagree with manifest hash/size")
                if job["source_sha256"] != digest:
                    issue(file_id, "job-hash", "job source hash disagrees with current source bytes")
            try:
                repo_db = _repository_db_for_source(project, manifest, repo_id, file_id)
                with connect(repo_db) as repo_con:
                    repo_file = repo_con.execute("SELECT * FROM files WHERE file_id=?", (file_id,)).fetchone()
                    repo_job_row = repo_con.execute("SELECT * FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
                    repo_tables = {r["name"] for r in repo_con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    repo_outputs = ([dict(r) for r in repo_con.execute(
                        "SELECT * FROM extraction_outputs WHERE source_file_id=? ORDER BY member_path", (file_id,))]
                        if "extraction_outputs" in repo_tables else [])
                    error_columns = {r["name"] for r in repo_con.execute("PRAGMA table_info(processing_errors)")}
                    error_key = "file_id" if "file_id" in error_columns else "file_path"
                    repo_errors = ([dict(r) for r in repo_con.execute(
                        f"SELECT * FROM processing_errors WHERE {error_key}=? AND phase='extraction'",
                        (file_id if error_key == "file_id" else expected_path,))]
                        if "processing_errors" in repo_tables else [])
                    repo_extractions = ([dict(r) for r in repo_con.execute(
                        "SELECT status,error FROM extractions WHERE file_id=?", (file_id,))]
                        if "extractions" in repo_tables else [])
                    if "archives" not in repo_tables:
                        repo_archives = []
                    else:
                        archive_columns = {r["name"] for r in repo_con.execute("PRAGMA table_info(archives)")}
                        archive_col = "status" if "status" in archive_columns else "payload_json"
                        archive_rows = [dict(r) for r in repo_con.execute(
                            f"SELECT {archive_col} FROM archives WHERE file_id=?", (file_id,))]
                        repo_archives = [({"status": r["status"]} if archive_col == "status" else
                                          {"payload_json": r["payload_json"]}) for r in archive_rows]
                    repo_has_output_table = "extraction_outputs" in repo_tables
                    job_columns = {r["name"] for r in repo_con.execute("PRAGMA table_info(extraction_jobs)")}
                    repo_has_dest = "destination" in job_columns
            except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
                issue(file_id, "repository-db", f"cannot inspect per-item DB: {type(exc).__name__}: {exc}")
                continue
            if repo_file is None:
                issue(file_id, "repository-file", "candidate is absent from per-item files")
            elif ((repo_file["repository_id"], repo_file["original_path"], repo_file["sha256"], repo_file["size_bytes"])
                  != (repo_id, expected_path, row.get("sha256"), row.get("size_bytes"))):
                issue(file_id, "repository-file", "per-item stable ID/path/hash/size disagrees with manifest")
            if job["status"] == "VERIFIED":
                checked["verified_outputs"] += 1
                if source is None:
                    issue(file_id, "verified-source", "VERIFIED job has no current source")
                destination = job.get("destination")
                try:
                    if not destination or Path(destination).is_absolute() or ".." in Path(destination).parts:
                        raise ValueError("unsafe extraction destination")
                    extraction_root = project / destination
                    metadata = json.loads((extraction_root / "extraction.json").read_text(encoding="utf-8"))
                    tree_hash, tree_bytes, actual_members = _digest_tree_members(extraction_root)
                    tree_valid = (metadata.get("source_sha256") == job["source_sha256"]
                                  and metadata.get("output_sha256") == tree_hash
                                  and metadata.get("output_bytes") == tree_bytes)
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    metadata = {}
                    tree_valid = False
                    issue(file_id, "published-tree", f"cannot verify extraction output: {type(exc).__name__}: {exc}")
                if not tree_valid:
                    issue(file_id, "published-tree", "published bytes, metadata digest, or source provenance failed verification")
                extracted_entries = [entry for entry in metadata.get("files", []) if entry.get("status") == "EXTRACTED"]
                expected_paths = {entry["member_path"] for entry in extracted_entries}
                if expected_paths != set(actual_members):
                    issue(file_id, "member-filesystem", "actual output paths differ from extracted metadata member set")
                expected_by_id = {hashlib.sha256(f"{file_id}:{entry['member_path']}".encode()).hexdigest(): entry
                                  for entry in extracted_entries}
                global_by_id = {r["extracted_file_id"]: r for r in global_outputs}
                if set(expected_by_id) != set(global_by_id):
                    issue(file_id, "global-output", "global extracted member IDs differ from extraction metadata")
                for out_id, entry in expected_by_id.items():
                    member = global_by_id.get(out_id)
                    relative = entry["member_path"]
                    expected_output_path = str((extraction_root / relative).relative_to(project))
                    if actual_members.get(relative) != (entry.get("sha256"), entry.get("size_bytes")):
                        issue(file_id, "member-hash", f"filesystem member hash/size differs from metadata: {relative}")
                    if (member is None or member["member_path"] != relative
                            or member["extracted_path"] != expected_output_path
                            or member["size_bytes"] != entry["size_bytes"] or member["sha256"] != entry["sha256"]
                            or member["status"] != "EXTRACTED"):
                        issue(file_id, "global-output-row", f"global member row differs from metadata: {relative}")
                if not repo_has_output_table:
                    issue(file_id, "output-mirror", "per-item database lacks extraction_outputs table")
                elif [tuple(r[c] for c in OUTPUT_COLUMNS) for r in global_outputs] != [
                        tuple(r[c] for c in OUTPUT_COLUMNS) for r in repo_outputs]:
                    issue(file_id, "output-mirror", "global and per-item extraction-output rows differ")
                repo_job_differs = (not repo_job_row or repo_job_row["status"] != "VERIFIED"
                    or repo_job_row["source_path"] != job["source_path"]
                    or repo_job_row["source_sha256"] != job["source_sha256"])
                if repo_job_row and repo_has_dest:
                    repo_job_differs = repo_job_differs or repo_job_row["destination"] != job["destination"]
                if repo_job_differs:
                    issue(file_id, "job-mirror", "per-item VERIFIED job provenance/destination differs")
            elif job["status"] in {"FAILED", "BLOCKED"}:
                checked["terminal_jobs"] += 1
                if not job["error"] or not job["next_action"] or job["attempts"] < 1:
                    issue(file_id, "terminal-record", "terminal job lacks error, next action, or attempt count")
                if not any(e["error"] == job["error"] and e["next_action"] == job["next_action"]
                           and e["retry_count"] == job["attempts"] for e in global_errors):
                    issue(file_id, "global-error", "global processing_errors lacks matching terminal error provenance")
                if not any(e.get("error") == job["error"] and e.get("next_action") == job["next_action"]
                           and e.get("retry_count") == job["attempts"] for e in repo_errors):
                    issue(file_id, "error-mirror", "per-item processing_errors lacks the matching terminal error")
                expected_file_status = "MISSING" if source_missing else job["status"]
                job_mirror_ok = (repo_job_row is not None and
                    (repo_job_row["status"], repo_job_row["source_path"], repo_job_row["source_sha256"],
                     repo_job_row["error"], repo_job_row["next_action"], repo_job_row["attempts"])
                    == (job["status"], job["source_path"], job["source_sha256"], job["error"],
                        job["next_action"], job["attempts"]))
                if not job_mirror_ok:
                    issue(file_id, "job-mirror", "terminal job provenance/error differs in per-item DB")
                if repo_file is not None and repo_file["status"] != expected_file_status:
                    issue(file_id, "file-status", f"per-item file status is {repo_file['status']}, expected {expected_file_status}")
                if (len(repo_extractions) != 1 or (repo_extractions[0]["status"], repo_extractions[0]["error"])
                        != (job["status"], job["error"])):
                    issue(file_id, "extraction-mirror", "per-item extraction record does not match terminal job")
                expected_archive = "MISSING" if source_missing else job["status"]
                global_archive = global_con.execute("SELECT payload_json FROM archives WHERE file_id=?", (file_id,)).fetchone()
                if global_archive:
                    try:
                        global_archive_status = json.loads(global_archive["payload_json"]).get("status")
                    except (TypeError, json.JSONDecodeError):
                        global_archive_status = None
                    if global_archive_status != expected_archive:
                        issue(file_id, "global-archive", f"global archive status is {global_archive_status}, expected {expected_archive}")
                if len(repo_archives) != 1:
                    issue(file_id, "archive-mirror", "per-item archive record is missing or duplicated")
                else:
                    try:
                        archive_status = (repo_archives[0].get("status") if "status" in repo_archives[0]
                                          else json.loads(repo_archives[0]["payload_json"]).get("status"))
                    except (TypeError, json.JSONDecodeError):
                        archive_status = None
                    if archive_status != expected_archive:
                        issue(file_id, "archive-mirror", f"per-item archive status is {archive_status}, expected {expected_archive}")
            else:
                issue(file_id, "job-state", f"candidate has nonterminal or unknown state {job['status']!r}")
    return {"offset": offset, "next_offset": min(offset + len(batch), len(candidates)),
            "candidate_total": len(candidates), "checked": checked, "issues": issues}


def _save_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with open(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def repair_missing_source(root: Path, project: Path, file_id: str) -> dict[str, Any]:
    """Reconcile a manifest-confirmed absent source as an explicit FAILED/MISSING_SOURCE record."""
    project = project.resolve(strict=True)
    manifest_path = project / "data/manifests/REPO_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next((item for item in manifest["files"] if _inventory_file_id(item) == file_id), None)
    if row is None or row.get("status") != "MISSING":
        raise ValueError(f"{file_id} is not explicitly MISSING in the manifest")
    source = root.resolve(strict=True) / row["original_path"]
    if source.exists() or source.is_symlink():
        raise ValueError(f"refusing missing-source repair because source now exists: {source}")
    repo_id = row["repository_id"]
    db_path = project / "data/database/private_ai_corpus.sqlite"
    error = f"MISSING_SOURCE: manifest retains {row['original_path']} but no source bytes exist at {source}"
    next_action = "await source restoration or explicit archival disposition; do not retry extraction until bytes are present"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    with connect(db_path) as con, con:
        job = con.execute("SELECT * FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
        if job is None or job["repository_id"] != repo_id or job["source_path"] != row["original_path"]:
            raise ValueError("global job identity/path does not match the stable manifest record")
        attempt = max(1, int(job["attempts"]))
        if job["source_sha256"] != row.get("sha256"):
            raise ValueError("global job hash does not preserve the manifest's original source identity")
        con.execute("UPDATE extraction_jobs SET detected_format=?,status='FAILED',destination=NULL,updated_at=?,lease_owner=NULL,lease_expires_at=NULL,attempts=?,error=?,next_action=? WHERE file_id=?",
                    (row.get("detected_format") or job["detected_format"], now, attempt, error, next_action, file_id))
        con.execute("UPDATE repository_files SET status='MISSING' WHERE file_id=?", (file_id,))
        archive_columns = {r["name"] for r in con.execute("PRAGMA table_info(archives)")}
        if "status" in archive_columns:
            con.execute("UPDATE archives SET status='MISSING' WHERE file_id=?", (file_id,))
        elif "payload_json" in archive_columns:
            con.execute("UPDATE archives SET payload_json=json_set(payload_json,'$.status','MISSING') WHERE file_id=?", (file_id,))
        existing = con.execute("SELECT 1 FROM processing_errors WHERE repository_id=? AND file_path=? AND phase='extraction' AND error=? AND retry_count=?",
                               (repo_id, row["original_path"], error, attempt)).fetchone()
        if existing is None:
            con.execute("INSERT INTO processing_errors(repository_id,file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?,?)",
                        (repo_id, row["original_path"], "extraction", error, "corpus_reconcile.py", "reconcile-v1",
                         now, attempt, next_action))
    per_item_db = _repository_db_for_source(project, manifest, repo_id, file_id)
    _ensure_repo_schema(per_item_db)
    _ensure_repo_job_schema(per_item_db)
    with connect(per_item_db) as con, con:
        per_item_job = con.execute("SELECT * FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
        if per_item_job is None or per_item_job["source_sha256"] != job["source_sha256"]:
            raise ValueError("per-item job is missing or its source hash disagrees with preserved provenance")
        con.execute("UPDATE files SET status='MISSING' WHERE file_id=?", (file_id,))
        con.execute("UPDATE extraction_jobs SET detected_format=?,status='FAILED',destination=NULL,updated_at=?,lease_owner=NULL,lease_expires_at=NULL,attempts=?,error=?,next_action=? WHERE file_id=?",
                    (row.get("detected_format") or job["detected_format"], now, attempt, error, next_action, file_id))
        con.execute("DELETE FROM extractions WHERE file_id=?", (file_id,))
        con.execute("INSERT INTO extractions(file_id,status,destination,tool,tool_version,timestamp,error) VALUES(?,'FAILED',NULL,'corpus_reconcile.py','reconcile-v1',?,?)",
                    (file_id, now, error))
        archive_columns = {r["name"] for r in con.execute("PRAGMA table_info(archives)")}
        if "status" in archive_columns:
            con.execute("UPDATE archives SET status='MISSING' WHERE file_id=?", (file_id,))
        elif "payload_json" in archive_columns:
            con.execute("UPDATE archives SET payload_json=json_set(payload_json,'$.status','MISSING') WHERE file_id=?", (file_id,))
        error_columns = {r["name"] for r in con.execute("PRAGMA table_info(processing_errors)")}
        if "file_id" in error_columns:
            match = con.execute("SELECT 1 FROM processing_errors WHERE file_id=? AND phase='extraction' AND error=?",
                                (file_id, error)).fetchone()
            if match is None:
                con.execute("INSERT INTO processing_errors(file_id,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,'extraction',?,'corpus_reconcile.py','reconcile-v1',?,?,?)",
                            (file_id, error, now, attempt, next_action))
        else:
            match = con.execute("SELECT 1 FROM processing_errors WHERE file_path=? AND phase='extraction' AND error=?",
                                (row["original_path"], error)).fetchone()
            if match is None:
                con.execute("INSERT INTO processing_errors(file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,'extraction',?,'corpus_reconcile.py','reconcile-v1',?,?,?)",
                            (row["original_path"], error, now, attempt, next_action))
    return {"file_id": file_id, "status": "FAILED_WITH_COMPLETE_RECORD", "source": str(source),
            "original_source_sha256": job["source_sha256"], "attempts": attempt, "error": error,
            "next_action": next_action, "global_db": str(db_path), "per_item_db": str(per_item_db)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("repo"))
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--all", action="store_true", help="audit every candidate in durable batches")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--report", type=Path, help="atomically checkpoint batch results to this JSON file")
    parser.add_argument("--repair-missing-source", metavar="FILE_ID", help="reconcile one manifest-confirmed absent source across both DBs")
    args = parser.parse_args()
    try:
        if args.repair_missing_source:
            result = repair_missing_source(args.root, args.project, args.repair_missing_source)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if not args.all:
            result = audit(args.root, args.project, offset=args.offset, limit=args.limit)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1 if result["issues"] else 0
        if not args.report or args.batch_size < 1:
            raise ValueError("--all requires --report and a positive --batch-size")
        manifest_path = args.project / "data/manifests/REPO_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidate_total = sum(row.get("node_type") == "file" and row.get("archive_status") == "candidate-not-expanded"
                              for row in manifest["files"])
        report_path = args.report
        if report_path.exists():
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            if saved.get("candidate_total") != candidate_total or saved.get("manifest_timestamp") != manifest.get("discovery_timestamp"):
                raise ValueError("existing report belongs to a different candidate manifest; preserve and choose a new report path")
            batches = {int(key): value for key, value in saved.get("batches", {}).items()}
        else:
            batches = {}
        for offset in range(0, candidate_total, args.batch_size):
            if offset in batches:
                continue
            batch = audit(args.root, args.project, offset=offset, limit=args.batch_size)
            batches[offset] = batch
            _save_report(report_path, {"candidate_total": candidate_total,
                "manifest_timestamp": manifest.get("discovery_timestamp"), "batches": {str(k): v for k, v in sorted(batches.items())}})
            print(json.dumps({"batch_offset": offset, "candidates": batch["checked"]["candidates"],
                              "issues": len(batch["issues"]), "report": str(report_path)}, sort_keys=True), flush=True)
        issues = [issue for offset in sorted(batches) for issue in batches[offset]["issues"]]
        print(json.dumps({"candidate_total": candidate_total, "batches": len(batches),
                          "issue_count": len(issues), "issues": issues, "report": str(report_path)},
                         indent=2, sort_keys=True))
        return 1 if issues else 0
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
