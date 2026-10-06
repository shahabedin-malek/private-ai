#!/usr/bin/env python3
"""Append a directory's immediate corpus items to an existing inventory without re-enumerating it.

This is intended for additive arrivals such as repo/new/*.zip. Source bytes are read-only;
outputs are generated under the project workspace. No archive contents are executed or extracted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .corpus_inventory import (
        GLOBAL_SCHEMA, atomic_write, connect, extend_global_schema, insert_repo_db,
        kind_for, stable_slug, walk_item,
    )
except ImportError:
    from corpus_inventory import (
        GLOBAL_SCHEMA, atomic_write, connect, extend_global_schema, insert_repo_db,
        kind_for, stable_slug, walk_item,
    )

CSV_FIELDS = ["repository_id", "repository_name", "original_path", "relative_path", "filename",
              "size_bytes", "sha256", "mime_type", "detected_format", "extension", "executable",
              "archive_status", "package_type", "discovery_timestamp", "node_type", "status"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def append(root: Path, output: Path, add_directory: Path, *, prefix: str = "new") -> dict[str, Any]:
    corpus = root.resolve(strict=True)
    project = output.resolve()
    add_dir = add_directory.resolve(strict=True)
    if not corpus.is_dir() or not add_dir.is_dir():
        raise ValueError("corpus and additive source must be directories")
    if add_dir == corpus or corpus not in add_dir.parents:
        raise ValueError("additive source must be a descendant of the corpus root")
    if project == corpus or corpus in project.parents:
        raise ValueError("generated output may not be inside the raw corpus")
    prefix_path = Path(prefix)
    if prefix_path.is_absolute() or ".." in prefix_path.parts:
        raise ValueError("prefix must be a confined relative path")

    manifest_path = project / "data/manifests/REPO_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing_paths = {row["original_path"] for row in manifest["repositories"]}
    names = sorted(os.listdir(add_dir))
    # Exclude previously inventoried additions so an interrupted/repeated run is idempotent.
    inventoried_names = {Path(path).name for path in existing_paths
                         if len(Path(path).parts) > 1 and Path(path).parts[0] == prefix_path.as_posix()}
    names = [name for name in names if name not in inventoried_names]
    if not names:
        return {"added": 0, "errors": [], "repository_ids": []}
    timestamp = now()
    candidates: list[dict[str, Any]] = []
    files_by_path: dict[str, list[dict[str, Any]]] = {}
    dirs_by_path: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        source = add_dir / name
        source_stat = source.lstat()
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError(f"additive item is not a regular file: {prefix_path / name}")
        relative = (prefix_path / name).as_posix()
        if relative in existing_paths:
            continue
        files, directories = walk_item(source, corpus)
        item = {
            "name": name, "original_path": relative, "device": source_stat.st_dev,
            "inode": source_stat.st_ino, "discovered_at": timestamp, "updated_at": timestamp,
            "kind": kind_for(name, False), "status": "DISCOVERED",
            "size_bytes": sum(f["size_bytes"] for f in files if f["node_type"] == "file"),
            "sha256": hashlib.sha256("\n".join(sorted(f["sha256"] or "" for f in files)).encode()).hexdigest(),
            "file_count": sum(f["node_type"] == "file" for f in files),
            "directory_count": len(directories), "source_stat": {
                "device": source_stat.st_dev, "inode": source_stat.st_ino, "mode": source_stat.st_mode,
                "size": source_stat.st_size, "mtime_ns": source_stat.st_mtime_ns,
            },
        }
        candidates.append(item)
        files_by_path[relative] = files
        dirs_by_path[relative] = directories

    if not candidates:
        return {"added": 0, "errors": [], "repository_ids": []}
    used = {row["repository_id"] for row in manifest["repositories"]}
    next_id = max((int(value[5:]) for value in used if value.startswith("REPO-") and value[5:].isdigit()), default=0) + 1
    for item in sorted(candidates, key=lambda value: value["original_path"]):
        while f"REPO-{next_id:04d}" in used:
            next_id += 1
        item["repository_id"] = f"REPO-{next_id:04d}"
        used.add(item["repository_id"])
        next_id += 1

    global_db = project / "data/database/private_ai_corpus.sqlite"
    # Per-item databases/workspaces are idempotent and use identities derived from existing maximum ID.
    for item in candidates:
        repo_id = item["repository_id"]
        workspace_name = f"{repo_id}-{stable_slug(item['name'])}"
        workspace = project / "data/repos" / workspace_name
        for folder in ("source", "extracted", "scraped", "db", "logs", "manifest", "research", "derived"):
            (workspace / folder).mkdir(parents=True, exist_ok=True)
        repo_item = {**item, "workspace_path": str(Path("data/repos") / workspace_name)}
        item_files = files_by_path[item["original_path"]]
        item_dirs = dirs_by_path[item["original_path"]]
        db_path = workspace / "db" / f"{stable_slug(item['name'])}.sqlite"
        insert_repo_db(repo_item, item_files, item_dirs, db_path)
        atomic_write(workspace / "source/README.md",
                     f"# Source reference\n\nRaw corpus material is preserved at `{corpus / item['original_path']}`. This directory intentionally holds no mutable copy of the source.\n")
        atomic_write(workspace / "manifest/repo.json", json.dumps(
            {"repository": repo_item, "files": item_files, "directories": item_dirs},
            indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    with connect(global_db) as con:
        con.executescript(GLOBAL_SCHEMA)
        extend_global_schema(con)
        with con:
            for item in candidates:
                repo_id = item["repository_id"]
                workspace_name = f"{repo_id}-{stable_slug(item['name'])}"
                con.execute("""INSERT INTO repositories VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(repository_id) DO UPDATE SET name=excluded.name,original_path=excluded.original_path,
                    workspace_path=excluded.workspace_path,kind=excluded.kind,status=excluded.status,
                    updated_at=excluded.updated_at,item_size=excluded.item_size,item_sha256=excluded.item_sha256,
                    file_count=excluded.file_count,directory_count=excluded.directory_count""",
                    (repo_id, item["name"], item["original_path"], workspace_name, item["kind"], item["status"],
                     item["discovered_at"], timestamp, item["size_bytes"], item["sha256"], item["file_count"], item["directory_count"]))
                for source_file in files_by_path[item["original_path"]]:
                    file_id = f"{repo_id}:{hashlib.sha256(source_file['relative_path'].encode()).hexdigest()[:20]}"
                    record = {**source_file, "repository_id": repo_id, "file_id": file_id,
                              "discovery_timestamp": item["discovered_at"]}
                    con.execute("""INSERT INTO repository_files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(file_id) DO UPDATE SET original_path=excluded.original_path,
                        relative_path=excluded.relative_path,filename=excluded.filename,extension=excluded.extension,
                        size_bytes=excluded.size_bytes,sha256=excluded.sha256,mime_type=excluded.mime_type,
                        detected_format=excluded.detected_format,executable=excluded.executable,
                        archive_status=excluded.archive_status,package_type=excluded.package_type,
                        node_type=excluded.node_type,discovery_timestamp=excluded.discovery_timestamp,status=excluded.status""",
                        (file_id, repo_id, record["original_path"], record["relative_path"], record["filename"],
                         record["extension"], record["size_bytes"], record["sha256"], record["mime_type"],
                         record["detected_format"], int(record["executable"]), record["archive_status"],
                         record["package_type"], record["node_type"], record["discovery_timestamp"], record["status"]))
                    con.execute("INSERT INTO file_hashes VALUES(?,?,?,?) ON CONFLICT(repository_id,relative_path) DO UPDATE SET sha256=excluded.sha256,size_bytes=excluded.size_bytes",
                                (repo_id, record["relative_path"], record["sha256"], record["size_bytes"]))
                    def add_entity(table: str, payload: dict[str, Any]) -> None:
                        record_id = hashlib.sha256(f"{table}:{repo_id}:{record['relative_path']}".encode()).hexdigest()
                        con.execute(f"INSERT OR REPLACE INTO {table}(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                    (record_id, repo_id, file_id, record["relative_path"], json.dumps(payload, sort_keys=True),
                                     record["original_path"], "HIGH", timestamp))
                    add_entity("file_metadata", {key: record[key] for key in (
                        "mime_type", "detected_format", "extension", "executable", "archive_status", "package_type", "source_stat")})
                    add_entity("text_content", {"sha256": record["sha256"], "size_bytes": record["size_bytes"], "status": "PENDING_PARSE"})
                    if record["archive_status"] == "candidate-not-expanded":
                        add_entity("archives", {"format": record["detected_format"], "status": "DISCOVERED"})
                    if record["package_type"] not in {"file", "archive"}:
                        add_entity("packages", {"type": record["package_type"], "format": record["detected_format"]})
                    if record["detected_format"] in {"elf", "pe-executable"} or record["executable"]:
                        add_entity("executables", {"format": record["detected_format"], "executable_bit": record["executable"]})
                con.execute("INSERT INTO processing_runs(phase,started_at,ended_at,status,details_json) VALUES(?,?,?,?,?)",
                            ("additive-inventory", item["discovered_at"], timestamp, "COMPLETED",
                             json.dumps({"repository_id": repo_id, "original_path": item["original_path"],
                                         "file_count": item["file_count"], "source_sha256": item["sha256"]}, sort_keys=True)))

    new_repositories = []
    new_files = []
    for item in candidates:
        # Keep the manifest workspace project-relative; the global DB stores only its basename.
        workspace_name = f"{item['repository_id']}-{stable_slug(item['name'])}"
        repo_item = {**item, "workspace_path": str(Path("data/repos") / workspace_name)}
        new_repositories.append(repo_item)
        for source_file in files_by_path[item["original_path"]]:
            new_files.append({**source_file, "repository_id": item["repository_id"],
                              "file_id": f"{item['repository_id']}:{hashlib.sha256(source_file['relative_path'].encode()).hexdigest()[:20]}",
                              "discovery_timestamp": item["discovered_at"]})
    manifest["repositories"] = sorted(manifest["repositories"] + new_repositories, key=lambda row: row["repository_id"])
    manifest["files"] = sorted(manifest["files"] + new_files, key=lambda row: (row["repository_id"], row["relative_path"]))
    manifest["discovery_timestamp"] = timestamp
    totals = manifest["totals"]
    totals["top_level_items"] = sum(row.get("status") != "MISSING" for row in manifest["repositories"])
    totals["regular_files"] = sum(row.get("node_type") == "file" and row.get("status") != "MISSING" for row in manifest["files"])
    totals["symlinks"] = sum(row.get("node_type") == "symlink" and row.get("status") != "MISSING" for row in manifest["files"])
    totals["bytes"] = sum(row.get("size_bytes", 0) for row in manifest["files"] if row.get("status") != "MISSING")
    totals["directories_below_items"] += sum(len(dirs_by_path[item["original_path"]]) for item in candidates)
    totals["physical_top_level_entries"] = len(os.listdir(corpus))
    represented_roots = {Path(row["original_path"]).parts[0] for row in manifest["repositories"]
                         if row.get("status") != "MISSING"}
    totals["unrepresented_top_level_entries"] = sorted(set(os.listdir(corpus)) - represented_roots)
    atomic_write(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    repo_names = {row["repository_id"]: row["name"] for row in manifest["repositories"]}
    for record in manifest["files"]:
        writer.writerow({**record, "repository_name": repo_names[record["repository_id"]]})
    atomic_write(project / "data/manifests/REPO_MANIFEST.csv", csv_buffer.getvalue())
    atomic_write(project / "data/manifests/REPO_INVENTORY.md",
                 "# Repository Corpus Inventory\n\n"
                 f"Generated: {timestamp}\n\nRaw source (read-only): `{corpus}`\n\n## Counts\n\n"
                 f"- Active top-level repository items: **{totals['top_level_items']}**\n"
                 f"- Regular files: **{totals['regular_files']}**\n- Source bytes: **{totals['bytes']}**\n"
                 f"- Nested directories: **{totals['directories_below_items']}**\n"
                 f"- Failed inventory items: **{totals.get('failed_items', 0)}**\n"
                 f"- Missing prior items: **{totals.get('missing_prior_items', 0)}**\n"
                 f"- Physical top-level entries: **{totals.get('physical_top_level_entries', 0)}**\n"
                 f"- Unrepresented top-level entries: **{len(totals.get('unrepresented_top_level_entries', []))}**\n\n"
                 "## Stable IDs\n\nPreviously assigned IDs are preserved; additive items receive IDs above the prior maximum.\n\n"
                 "Raw source is inventoried only; archives are not extracted or executed by this command.\n")
    return {"added": len(candidates), "repository_ids": [item["repository_id"] for item in candidates],
            "file_records": len(new_files), "bytes": sum(item["size_bytes"] for item in candidates),
            "totals": totals, "errors": []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("repo"))
    parser.add_argument("--add-directory", type=Path, default=Path("repo/new"))
    parser.add_argument("--output", type=Path, default=Path("."))
    parser.add_argument("--prefix", default="new", help="path component retained in raw source references")
    args = parser.parse_args()
    try:
        result = append(args.root, args.output, args.add_directory, prefix=args.prefix)
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
