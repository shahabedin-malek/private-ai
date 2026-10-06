#!/usr/bin/env python3
"""Stage and safely extract newly added ZIP repositories in bounded resumable batches.

Only immutable ZIP copies are staged under the configured SSD scratch root. Extraction
outputs and authoritative SQLite databases remain in the project workspace. Corpus bytes
are never executed or modified. Scratch usage is hard-capped and source hashes are checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

try:
    from .corpus_extract import ExtractLimits, run as run_extract
    from .corpus_inventory import atomic_write
    from .processing_workspace import initialize_workspace
except ImportError:
    from corpus_extract import ExtractLimits, run as run_extract
    from corpus_inventory import atomic_write
    from processing_workspace import initialize_workspace

SCRATCH_SUBDIR = "private-ai-new-sources"
PRIORITY_WORDS = ("system-prompt", "system_prompt", "prompt", "typesafe", "jev")


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def scratch_usage(root: Path) -> int:
    total = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in list(dirs):
            if (base_path / name).is_symlink():
                raise ValueError("scratch root contains a symlinked directory")
        for name in files:
            item = base_path / name
            if item.is_symlink():
                raise ValueError("scratch root contains a symlinked file")
            st = item.stat(follow_symlinks=False)
            if not item.is_file() or st.st_size < 0:
                raise ValueError("scratch root contains a non-regular file")
            total += st.st_size
    return total


def stage_sources(project: Path, corpus: Path, scratch_root: Path, cap_bytes: int) -> tuple[Path, int]:
    manifest = json.loads((project / "data/manifests/REPO_MANIFEST.json").read_text(encoding="utf-8"))
    new_root = corpus / "new"
    if new_root.is_symlink() or not new_root.is_dir():
        raise ValueError("new repository source root is missing or not a regular directory")
    filesystem_names: set[str] = set()
    for entry in new_root.iterdir():
        if entry.is_symlink() or not entry.is_file():
            raise ValueError(f"new repository source is not a regular top-level file: {entry.name}")
        filesystem_names.add(entry.name)

    new_repositories = [row for row in manifest["repositories"]
                        if row.get("original_path", "").startswith("new/") and row.get("status") != "MISSING"]
    new_repositories.sort(key=lambda row: row["repository_id"])
    names_by_path: dict[str, dict[str, Any]] = {}
    repository_ids: set[str] = set()
    for repository in new_repositories:
        relative = repository.get("original_path", "")
        parts = Path(relative).parts
        if (Path(relative).is_absolute() or len(parts) != 2 or parts[0] != "new"
                or parts[1] in {"", ".", ".."} or relative != f"new/{parts[1]}"):
            raise ValueError(f"unsafe or unsupported new repository path: {relative!r}")
        if parts[1] in names_by_path:
            raise ValueError(f"duplicate new repository manifest path: {relative}")
        repo_id = repository.get("repository_id")
        if not repo_id or repo_id in repository_ids:
            raise ValueError(f"missing or duplicate new repository ID for {relative}")
        names_by_path[parts[1]] = repository
        repository_ids.add(repo_id)
    manifest_names = set(names_by_path)
    if filesystem_names != manifest_names:
        missing = sorted(manifest_names - filesystem_names)
        untracked = sorted(filesystem_names - manifest_names)
        raise ValueError(f"new source/manifest mismatch: missing={missing[:5]}, untracked={untracked[:5]}")

    files_by_repository: dict[str, list[dict[str, Any]]] = {}
    for row in manifest["files"]:
        if row.get("repository_id") in repository_ids and row.get("node_type") == "file":
            files_by_repository.setdefault(row["repository_id"], []).append(row)

    current_usage = scratch_usage(scratch_root)
    if current_usage > cap_bytes:
        raise ValueError(f"scratch usage {current_usage} exceeds cap {cap_bytes}")
    stage_root = scratch_root / SCRATCH_SUBDIR
    if stage_root.is_symlink():
        raise ValueError("unsafe symlinked source-staging directory")
    if stage_root.exists() and (stage_root.is_symlink() or not stage_root.is_dir()):
        raise ValueError("unsafe existing source-staging directory")
    staged_corpus = stage_root / "corpus"
    if staged_corpus.exists() and (staged_corpus.is_symlink() or not staged_corpus.is_dir()):
        raise ValueError("unsafe existing staged-corpus directory")
    staged_new = staged_corpus / "new"
    if staged_new.exists() and (staged_new.is_symlink() or not staged_new.is_dir()):
        raise ValueError("unsafe existing staged new-repository directory")
    staged_new.mkdir(parents=True, exist_ok=True)
    source_bytes = 0
    for repository in new_repositories:
        relative = repository["original_path"]
        source = new_root / Path(relative).name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"source is missing or not a regular file: {relative}")
        file_rows = files_by_repository.get(repository["repository_id"], [])
        expected = next((row for row in file_rows if row.get("original_path") == relative), None)
        if len(file_rows) != 1 or expected is None or not expected.get("sha256"):
            raise ValueError(f"manifest file identity is incomplete for {repository['repository_id']}")
        if expected.get("size_bytes") is None:
            raise ValueError(f"manifest file size is incomplete for {repository['repository_id']}")
        target = staged_corpus / relative
        if target.parent != staged_new:
            raise ValueError(f"staged path is outside the expected source directory: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise ValueError(f"unsafe existing scratch source: {relative}")
            actual_hash, actual_size = sha256_file(target)
            if (actual_hash, actual_size) != (expected["sha256"], expected["size_bytes"]):
                raise ValueError(f"staged source checksum mismatch: {relative}")
            source_bytes += actual_size
            continue
        source_size = source.stat().st_size
        projected = current_usage + source_size
        if projected > cap_bytes:
            raise ValueError(f"staging {relative} would exceed scratch cap {cap_bytes}")
        if source_size != expected["size_bytes"]:
            raise ValueError(f"raw source size differs from manifest: {relative}")
        digest = hashlib.sha256()
        size = 0
        temp = target.with_name(target.name + ".partial")
        if temp.exists() or temp.is_symlink():
            raise ValueError(f"unreconciled partial scratch file requires inspection: {relative}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(source, flags)
        try:
            with os.fdopen(fd, "rb") as reader, temp.open("xb") as writer:
                while block := reader.read(1024 * 1024):
                    size += len(block)
                    if size > expected["size_bytes"] or current_usage + size > cap_bytes:
                        raise ValueError(f"source grew during SSD staging or cap would be exceeded: {relative}")
                    digest.update(block)
                    writer.write(block)
                writer.flush()
                os.fsync(writer.fileno())
            if (digest.hexdigest(), size) != (expected["sha256"], expected["size_bytes"]):
                raise ValueError(f"raw source hash/size differs from manifest: {relative}")
            os.replace(temp, target)
        except Exception:
            temp.unlink(missing_ok=True)
            raise
        current_usage += size
        source_bytes += size
    return staged_corpus, source_bytes


def priority(repository: dict[str, Any]) -> tuple[int, str, str]:
    name = repository.get("name", "").lower()
    category = 0 if any(word in name for word in PRIORITY_WORDS) else 1
    return category, repository["repository_id"], name


def queue_priority(repository: dict[str, Any], db: Path) -> tuple[int, int, str, str]:
    """Prefer never-attempted inputs so one costly resumable archive cannot starve the queue."""
    state = extraction_state(db, repository["repository_id"])
    if state is None:
        state_rank = 0
    elif state["status"] == "FAILED" and state["attempts"] < 3:
        state_rank = 1
    elif state["status"] == "IN_PROGRESS" and (
            not state.get("lease_expires_at") or state["lease_expires_at"] <= time.time()):
        state_rank = 2
    elif state["status"] == "IN_PROGRESS":
        state_rank = 3
    else:
        state_rank = 4
    category, repo_id, name = priority(repository)
    return state_rank, category, repo_id, name



def extraction_state(db: Path, repository_id: str) -> dict[str, Any] | None:
    con = sqlite3.connect(db, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT status,attempts,error,next_action,lease_owner,lease_expires_at FROM extraction_jobs WHERE repository_id=?",
                          (repository_id,)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def run_batch(project: Path, corpus: Path, scratch: Path, *, cap_bytes: int,
              batch_size: int, wall_seconds: float, per_call_seconds: int) -> dict[str, Any]:
    project = project.resolve(strict=True)
    corpus = corpus.resolve(strict=True)
    scratch = scratch.resolve(strict=True)
    if cap_bytes < 1 or cap_bytes > 20 * 1024**3:
        raise ValueError("scratch cap must be between 1 byte and 20 GiB")
    if scratch == project or project in scratch.parents:
        raise ValueError("SSD scratch must not be inside the project workspace")
    scratch_status = initialize_workspace(scratch, project=project, cap_bytes=cap_bytes)
    staged_corpus, staged_source_bytes = stage_sources(project, corpus, scratch, cap_bytes)
    manifest_path = project / "data/manifests/REPO_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    db = project / "data/database/private_ai_corpus.sqlite"
    repositories = sorted(
        (row for row in manifest["repositories"]
         if row.get("original_path", "").startswith("new/") and row.get("status") != "MISSING"),
        key=lambda row: queue_priority(row, db),
    )
    deadline = time.monotonic() + wall_seconds
    outcomes: list[dict[str, Any]] = []
    processed_repo_ids: set[str] = set()
    considered = 0
    for repository in repositories:
        if considered >= batch_size or time.monotonic() >= deadline:
            break
        repo_id = repository["repository_id"]
        state = extraction_state(db, repo_id)
        if state and state["status"] in {"VERIFIED", "BLOCKED"}:
            continue
        if state and state["status"] == "FAILED" and state["attempts"] >= 3:
            continue
        considered += 1
        repo_results: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            limits = ExtractLimits(
                max_input_bytes=1024 * 1024 * 1024,
                max_members=10_000,
                max_member_bytes=128 * 1024 * 1024,
                max_total_bytes=1024 * 1024 * 1024,
                max_compression_ratio=200.0,
                max_depth=4,
                max_wall_seconds=per_call_seconds,
                min_free_bytes=256 * 1024 * 1024,
                max_attempts=3,
            )
            result = run_extract(staged_corpus, project, repo_id=repo_id, limit=1,
                                 owner=f"new-batch-{os.getpid()}", lease_seconds=300, limits=limits)
            repo_results.append({key: result[key] for key in (
                "verified", "skipped_verified", "blocked", "failed", "paused", "terminal_records_mirrored")})
            leaf = result.get("results", [])
            status = leaf[-1].get("status") if leaf else None
            if status != "PAUSED":
                break
        current = extraction_state(db, repo_id)
        processed_repo_ids.add(repo_id)
        outcomes.append({"repository_id": repo_id, "status": current["status"] if current else "PENDING",
                         "attempts": current["attempts"] if current else 0,
                         "passes": len(repo_results), "results": repo_results})
        checkpoint = {
            "task_id": "CORPUS-0006-NEW-ZIPS", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "phase": "PHASE 5 — new-repository extraction", "stage": "incremental recursive extraction",
            "batch_size": batch_size, "wall_seconds": wall_seconds,
            "database_status_counts": _count_statuses(_status_rows(repositories, db)),
            "next_exact_action": "Resume staged extraction for the next nonterminal priority repository using a bounded worker call; verify output and database mirrors.",
            "scratch_path": str(scratch / SCRATCH_SUBDIR), "scratch_cap_bytes": cap_bytes,
            "scratch_usage_bytes": scratch_usage(scratch), "ssd_write_verified": scratch_status["probe_verified"],
            "staged_source_bytes": staged_source_bytes,
            "outcomes": outcomes,
        }
        atomic_write(project / ".progress/NEW_REPO_EXTRACTION_PROGRESS.json",
                     json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    state_rows = _status_rows(repositories, db)
    for repository in repositories:
        state = extraction_state(db, repository["repository_id"])
        status = next(status for repo_id, status in state_rows if repo_id == repository["repository_id"])
        if repository["repository_id"] not in processed_repo_ids and (not state or state["status"] not in {"VERIFIED", "BLOCKED"}) and not (state and state["status"] == "FAILED" and state["attempts"] >= 3):
            outcomes.append({"repository_id": repository["repository_id"],
                             "status": state["status"] if state else "PENDING",
                             "attempts": state["attempts"] if state else 0,
                             "passes": 0, "results": [], "deferred_this_batch": True})
    counts: dict[str, int] = {}
    for _, status in state_rows:
        counts[status] = counts.get(status, 0) + 1
    final_checkpoint = {
        "task_id": "CORPUS-0006-NEW-ZIPS", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_items": len(repositories), "total_new_repositories": len(repositories),
        "phase": "PHASE 5 — new-repository extraction", "status_counts": counts,
        "database_status_counts": _count_statuses(state_rows),
        "processed_this_batch": considered, "deferred_this_batch": sum(bool(item.get("deferred_this_batch")) for item in outcomes),
        "staged_source_bytes": staged_source_bytes,
        "scratch_usage_bytes": scratch_usage(scratch), "scratch_cap_bytes": cap_bytes,
        "ssd_write_verified": scratch_status["probe_verified"],
        "python_tempdir": scratch_status["python_tempdir"],
        "processing_device": scratch_status["root_device"],
        "project_device": scratch_status["project_device"],
        "next_exact_action": "Resume `python3 scripts/corpus_new_batch.py --project . --corpus repo --scratch /home/chris/data-processing --batch-size 12 --wall-seconds 240 --per-call-seconds 35`; queue scheduling now favors never-attempted inputs so paused large archives cannot starve pending sources. Afterward reconcile extraction_jobs, output hashes, per-item mirrors, SSD quota, and parser pending count.",
        "outcomes": outcomes,
    }
    atomic_write(project / ".progress/NEW_REPO_EXTRACTION_PROGRESS.json",
                 json.dumps(final_checkpoint, indent=2, sort_keys=True) + "\n")
    return final_checkpoint


def _status_rows(repositories: list[dict[str, Any]], db: Path) -> list[tuple[str, str]]:
    state_rows = []
    for repository in repositories:
        state = extraction_state(db, repository["repository_id"])
        status = state["status"] if state else "PENDING"
        if (status == "IN_PROGRESS" and "lease_expires_at" in state
                and (not state["lease_expires_at"] or state["lease_expires_at"] <= time.time())):
            status = "PAUSED"
        state_rows.append((repository["repository_id"], status))
    return state_rows


def _count_statuses(state_rows: list[tuple[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, status in state_rows:
        counts[status] = counts.get(status, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--corpus", type=Path, default=Path("repo"))
    parser.add_argument("--scratch", type=Path, default=Path("/home/chris/data-processing"))
    parser.add_argument("--cap-gb", type=float, default=20.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--wall-seconds", type=float, default=420.0)
    parser.add_argument("--per-call-seconds", type=int, default=35)
    args = parser.parse_args()
    try:
        if args.batch_size < 1 or args.wall_seconds <= 0 or args.per_call_seconds < 1:
            raise ValueError("batch and time bounds must be positive")
        result = run_batch(args.project, args.corpus, args.scratch,
                           cap_bytes=int(args.cap_gb * 1024**3), batch_size=args.batch_size,
                           wall_seconds=args.wall_seconds, per_call_seconds=args.per_call_seconds)
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr, flush=True)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
