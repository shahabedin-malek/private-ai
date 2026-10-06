#!/usr/bin/env python3
"""Safely extract supported corpus containers without running their contents.

The raw corpus is read-only. Extraction is staged under the per-repository workspace and published by
atomic rename only after all supported members pass validation. A killed worker leaves only a private
staging directory; its durable lease expires and a retry discards staging and repeats idempotently.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import bz2
import gzip
import hashlib
import json
import lzma
import os
import shutil
import sqlite3
import stat
import sys
import tarfile
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterator

CHUNK = 1024 * 1024
PIPELINE_VERSION = "safe-extract-v6"
JOB_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS extraction_jobs (
 file_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL REFERENCES repositories(repository_id),
 source_path TEXT NOT NULL, source_sha256 TEXT NOT NULL, detected_format TEXT NOT NULL,
 status TEXT NOT NULL, destination TEXT, started_at TEXT, updated_at TEXT NOT NULL,
 lease_owner TEXT, lease_expires_at REAL, attempts INTEGER NOT NULL DEFAULT 0,
 error TEXT, next_action TEXT NOT NULL DEFAULT '', pipeline_version TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON extraction_jobs(status,lease_expires_at);
CREATE TABLE IF NOT EXISTS extraction_outputs (
 extracted_file_id TEXT PRIMARY KEY, source_file_id TEXT NOT NULL REFERENCES repository_files(file_id),
 repository_id TEXT NOT NULL REFERENCES repositories(repository_id), member_path TEXT NOT NULL,
 extracted_path TEXT NOT NULL, parent_archive TEXT NOT NULL, depth INTEGER NOT NULL,
 size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, detected_format TEXT NOT NULL,
 status TEXT NOT NULL, tool TEXT NOT NULL, tool_version TEXT NOT NULL, processed_at TEXT NOT NULL,
 UNIQUE(source_file_id,extracted_path)
);
CREATE INDEX IF NOT EXISTS idx_extraction_outputs_source ON extraction_outputs(source_file_id);
CREATE TABLE IF NOT EXISTS schema_migrations (
 version TEXT PRIMARY KEY, timestamp TEXT NOT NULL, migration TEXT NOT NULL,
 reason TEXT NOT NULL, status TEXT NOT NULL, error TEXT
);
"""


def timestamp() -> str:
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


@dataclass(frozen=True)
class ExtractLimits:
    max_input_bytes: int = 512 * 1024 * 1024
    max_members: int = 10_000
    max_member_bytes: int = 32 * 1024 * 1024
    max_total_bytes: int = 256 * 1024 * 1024
    max_compression_ratio: float = 200.0
    max_depth: int = 4
    max_path_length: int = 240
    max_wall_seconds: int = 300
    min_free_bytes: int = 256 * 1024 * 1024
    max_attempts: int = 3

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if name == "max_compression_ratio":
                if value <= 0:
                    raise ValueError(f"{name} must be positive")
            elif name == "max_depth":
                if value < 0:
                    raise ValueError(f"{name} must be non-negative")
            elif name in {"min_free_bytes", "max_attempts"}:
                if value < 0 or (name == "max_attempts" and value < 1):
                    raise ValueError(f"{name} has an invalid bound")
            elif value < 1:
                raise ValueError(f"{name} must be positive")


@dataclass
class Member:
    name: str
    size: int
    compressed_size: int
    kind: str
    opener: Any
    container: Any = None
    checksum: int | None = None


class ExtractionRefusal(Exception):
    """A typed refusal for hostile or out-of-policy input."""


class ExtractionPaused(Exception):
    """A resumable pause before the worker's wall-time budget is exhausted."""


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise OSError("source is not a non-symlink regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError("source changed type or identity while opening")
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def detect_format(path: Path) -> str:
    """Signature-first detection for supported read-only formats."""
    with path.open("rb") as stream:
        head = stream.read(512)
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")) or zipfile.is_zipfile(path):
        return "zip"
    if len(head) >= 265 and head[257:262] == b"ustar":
        return "tar"
    # tarfile handles older tar dialects and compressed tar streams by parsing structure, not extension.
    try:
        with tarfile.open(path, mode="r:*") as archive:
            archive.next()
        return "tar"
    except (tarfile.TarError, OSError, EOFError):
        pass
    if head.startswith(b"\x1f\x8b"):
        return "gzip"
    if head.startswith(b"BZh"):
        return "bzip2"
    if head.startswith(b"\xfd7zXZ\x00"):
        return "xz"
    if head.startswith(b"!<arch>\n"):
        return "ar-unsupported"
    return "unsupported"


def safe_member_path(name: str, *, max_path_length: int) -> str:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ExtractionRefusal("empty or NUL-containing member name")
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        raise ExtractionRefusal("absolute member path")
    if len(normalized) > max_path_length:
        raise ExtractionRefusal("member path exceeds configured length")
    normalized = normalized.rstrip("/")
    parts = normalized.split("/")
    if not normalized or any(part in ("", ".", "..") for part in parts):
        raise ExtractionRefusal("non-canonical or traversing member path")
    if len(parts[0]) >= 2 and parts[0][1] == ":":
        raise ExtractionRefusal("drive-letter member path")
    forbidden = set('<>:"|?*')
    for part in parts:
        if any(ord(char) < 32 or char in forbidden for char in part):
            raise ExtractionRefusal("member path contains non-portable or special characters")
        if part.endswith((".", " ")):
            raise ExtractionRefusal("member path has a Windows-ambiguous trailing dot or space")
        if part.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            raise ExtractionRefusal("member path contains a reserved device name")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or pure.as_posix() != normalized or any(part in (".", "..") for part in pure.parts):
        raise ExtractionRefusal("unsafe normalized member path")
    return normalized


def _open_compressed(path: Path, fmt: str) -> BinaryIO:
    raw = path.open("rb")
    try:
        if fmt == "gzip":
            reader = gzip.GzipFile(fileobj=raw, mode="rb")
        elif fmt == "bzip2":
            reader = bz2.BZ2File(raw, mode="rb")
        elif fmt == "xz":
            reader = lzma.LZMAFile(raw, mode="rb")
        else:
            raise ExtractionRefusal(f"unsupported compression format: {fmt}")
        return _OwnedStream(reader, raw)
    except Exception:
        raw.close()
        raise


class _OwnedStream:
    def __init__(self, reader: BinaryIO, owner: BinaryIO) -> None:
        self.reader, self.owner = reader, owner

    def read(self, size: int = -1) -> bytes:
        return self.reader.read(size)

    def close(self) -> None:
        try:
            self.reader.close()
        finally:
            self.owner.close()


def _open_zip_member(path: Path, index: int) -> BinaryIO:
    archive = zipfile.ZipFile(path)
    try:
        info = archive.infolist()[index]
        return _ZipStream(archive.open(info, "r"), archive)
    except Exception:
        archive.close()
        raise


def _zip_members(path: Path, max_members: int) -> list[Member]:
    members: list[Member] = []
    archive = zipfile.ZipFile(path)
    try:
        infos = archive.infolist()
        if len(infos) > max_members:
            raise ExtractionRefusal(f"member count {len(infos)} exceeds limit {max_members}")
        if any(info.flag_bits & 0x1 for info in infos):
            raise ExtractionRefusal("encrypted ZIP members are unsupported")
        for info in infos:
            mode = (info.external_attr >> 16) & 0o170000
            if info.is_dir() or info.filename.endswith("/"):
                kind = "directory"
            elif mode == stat.S_IFLNK:
                kind = "symlink"
            elif mode not in (0, stat.S_IFREG):
                kind = "special"
            else:
                kind = "file"
            members.append(Member(info.filename, int(info.file_size), int(info.compress_size), kind,
                                  lambda info=info, archive=archive: archive.open(info, "r"), archive,
                                  info.CRC if kind == "file" else None))
        return members
    except Exception:
        archive.close()
        raise
    finally:
        # The returned member openers retain the shared archive until their streams close.
        if not members:
            archive.close()


class _ZipStream:
    def __init__(self, stream: BinaryIO, archive: zipfile.ZipFile) -> None:
        self.stream, self.archive = stream, archive

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def close(self) -> None:
        self.stream.close()
        self.archive.close()


def _open_tar_member(path: Path, index: int) -> BinaryIO:
    archive = tarfile.open(path, mode="r:*")
    try:
        for current, info in enumerate(archive):
            if current == index:
                stream = archive.extractfile(info)
                if stream is None:
                    archive.close()
                    raise ExtractionRefusal("tar member has no readable regular-file payload")
                return _TarStream(archive, stream)
        raise ExtractionRefusal("tar member index disappeared between listing and reading")
    except Exception:
        archive.close()
        raise


def _open_tar_member_from_archive(archive: tarfile.TarFile, info: tarfile.TarInfo) -> BinaryIO:
    stream = archive.extractfile(info)
    if stream is None:
        raise ExtractionRefusal("tar member has no readable regular-file payload")
    return _TarStream(archive, stream, close_archive=False)


class _TarStream:
    def __init__(self, archive: tarfile.TarFile, stream: BinaryIO, *, close_archive: bool = True) -> None:
        self.archive, self.stream, self.close_archive = archive, stream, close_archive

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def close(self) -> None:
        self.stream.close()
        if self.close_archive:
            self.archive.close()


def _tar_members(path: Path, max_members: int) -> list[Member]:
    archive = tarfile.open(path, mode="r:*")
    members: list[Member] = []
    try:
        for index, info in enumerate(archive):
            if index >= max_members:
                raise ExtractionRefusal(f"member count exceeds limit {max_members}")
            if info.isdir():
                kind = "directory"
            elif info.issym():
                kind = "symlink"
            elif info.islnk():
                kind = "hardlink"
            elif info.isreg():
                kind = "file"
            else:
                kind = "special"
            members.append(Member(info.name, int(info.size), int(info.size), kind,
                                  lambda info=info, archive=archive: _open_tar_member_from_archive(archive, info), archive))
        return members
    except Exception:
        archive.close()
        raise
    finally:
        if not members:
            archive.close()


def list_members(path: Path, fmt: str, max_members: int) -> list[Member]:
    if fmt == "zip":
        return _zip_members(path, max_members)
    if fmt == "tar":
        return _tar_members(path, max_members)
    if fmt in {"gzip", "bzip2", "xz"}:
        name = path.name
        output_name = name
        for suffix in (".gz", ".bz2", ".xz"):
            if output_name.lower().endswith(suffix):
                output_name = output_name[:-len(suffix)]
                break
        if output_name == name or not output_name:
            output_name = name + ".decompressed"
        return [Member(output_name, 0, path.stat().st_size, "file",
                       lambda path=path, fmt=fmt: _open_compressed(path, fmt))]
    raise ExtractionRefusal(f"unsupported archive format: {fmt}")


def _validate_members(members: list[Member], limits: ExtractLimits) -> list[tuple[Member, str]]:
    if len(members) > limits.max_members:
        raise ExtractionRefusal(f"member count {len(members)} exceeds limit {limits.max_members}")
    planned: list[tuple[Member, str]] = []
    seen: set[str] = set()
    kinds: dict[str, str] = {}
    declared_total = 0
    canonical_components: dict[str, str] = {}
    for member in members:
        if member.kind not in {"file", "directory"}:
            raise ExtractionRefusal(f"unsafe {member.kind} member: {member.name!r}")
        target = safe_member_path(member.name, max_path_length=limits.max_path_length)
        folded = target.casefold()
        if folded in seen:
            raise ExtractionRefusal(f"duplicate/case-colliding member path: {target!r}")
        seen.add(folded)
        components = PurePosixPath(target).parts
        for index in range(len(components)):
            prefix = PurePosixPath(*components[:index + 1]).as_posix()
            previous = canonical_components.setdefault(prefix.casefold(), prefix)
            if previous != prefix:
                raise ExtractionRefusal(f"case-colliding path component: {prefix!r}")
        kinds[target] = member.kind
        if member.kind == "file":
            if member.size < 0 or member.size > limits.max_member_bytes:
                raise ExtractionRefusal(f"declared member size exceeds limit: {target!r}")
            declared_total += member.size
            if declared_total > limits.max_total_bytes:
                raise ExtractionRefusal("declared uncompressed total exceeds limit")
            if member.size:
                ratio = member.size / max(member.compressed_size, 1)
                if ratio > limits.max_compression_ratio:
                    raise ExtractionRefusal(f"compression ratio {ratio:.1f} exceeds limit for {target!r}")
        planned.append((member, target))
    for _, target in planned:
        parts = PurePosixPath(target).parts
        for index in range(1, len(parts)):
            ancestor = PurePosixPath(*parts[:index]).as_posix()
            if kinds.get(ancestor) == "file":
                raise ExtractionRefusal(f"file-as-parent conflict: {ancestor!r}")
    return planned


def _write_member(member: Member, target: Path, limits: ExtractLimits, budget: list[int], deadline: float) -> tuple[int, str]:
    stream = member.opener()
    digest = hashlib.sha256()
    written = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.name}.{os.urandom(8).hex()}.partial")
    try:
        with partial.open("xb") as output:
            while True:
                if time.monotonic() > deadline:
                    raise ExtractionPaused("archive processing wall-time budget reached")
                chunk = stream.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                budget[0] += len(chunk)
                if written > limits.max_member_bytes:
                    raise ExtractionRefusal(f"actual member bytes exceed limit: {member.name!r}")
                if budget[0] > limits.max_total_bytes:
                    raise ExtractionRefusal("actual archive bytes exceed total limit")
                if shutil.disk_usage(target.parent).free < limits.min_free_bytes:
                    raise ExtractionRefusal("available disk space fell below configured safety floor")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
            if member.size and written != member.size:
                raise ExtractionRefusal(f"member size mismatch for {member.name!r}: declared {member.size}, read {written}")
            if member.checksum is not None and getattr(stream, "_running_crc", None) != member.checksum:
                raise ExtractionRefusal(f"member CRC mismatch for {member.name!r}")

        os.chmod(partial, 0o644)
        os.replace(partial, target)
        return written, digest.hexdigest()
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    finally:
        stream.close()


def _verify_staged_member(member: Member, target: Path, *, expected_size: int, expected_sha256: str,
                         limits: ExtractLimits, deadline: float) -> None:
    """Confirm journaled bytes still equal the bytes yielded by the verified source archive."""
    digest = hashlib.sha256()
    size = 0
    stream = member.opener()
    try:
        while True:
            if time.monotonic() > deadline:
                raise ExtractionPaused("archive processing wall-time budget reached while recovering staging")
            chunk = stream.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > limits.max_member_bytes:
                raise ExtractionRefusal(f"recovered source member exceeds configured bound: {member.name!r}")
            digest.update(chunk)
        if size != expected_size or digest.hexdigest() != expected_sha256:
            raise ExtractionRefusal(f"journaled output does not match source archive member: {member.name!r}")
        if member.size and size != member.size:
            raise ExtractionRefusal(f"source member size mismatch during staging recovery: {member.name!r}")
    finally:
        stream.close()
    output_hash, output_size = sha256_file(target)
    if output_size != expected_size or output_hash != expected_sha256:
        raise ExtractionRefusal(f"journaled output changed during staging recovery: {member.name!r}")


def _close_member_container(members: list[Member]) -> None:
    """Close the shared archive container once all its member streams are consumed."""
    if members and members[0].container is not None:
        members[0].container.close()


def _nested_format(path: Path) -> str:
    try:
        return detect_format(path)
    except (OSError, zipfile.BadZipFile, tarfile.TarError):
        return "unsupported"


def _relative_outputs(stage: Path) -> set[str]:
    found: set[str] = set()
    for current, dirnames, filenames in os.walk(stage, followlinks=False):
        for name in dirnames + filenames:
            path = Path(current) / name
            if path.is_symlink():
                raise ExtractionRefusal("symlink appeared in extraction staging output")
            if path.is_file() and name != ".extraction-journal.jsonl":
                found.add(path.relative_to(stage).as_posix())
    return found


def _journal_record(stage: Path, record: dict[str, Any]) -> None:
    journal = stage / ".extraction-journal.jsonl"
    with journal.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _load_staging_records(stage: Path) -> dict[str, dict[str, Any]]:
    """Load only journaled staging outputs whose paths, bytes and hashes still verify."""
    journal = stage / ".extraction-journal.jsonl"
    if journal.is_symlink():
        raise ExtractionRefusal("staging journal is a symlink")
    records: dict[str, dict[str, Any]] = {}
    if journal.is_file():
        for line_number, line in enumerate(journal.read_text(encoding="utf-8").splitlines(), start=1):
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExtractionRefusal(f"staging journal is corrupt at line {line_number}") from exc
            if not isinstance(record, dict) or record.get("status") not in {"EXTRACTED", "DIRECTORY", "BLOCKED_UNSUPPORTED"}:
                raise ExtractionRefusal(f"staging journal has an invalid record at line {line_number}")
            member_path = record.get("member_path")
            safe_member_path(member_path, max_path_length=4096)
            records[member_path] = record
    expected_files: set[str] = set()
    for member_path, record in records.items():
        target = stage.joinpath(*PurePosixPath(member_path).parts)
        if record["status"] == "EXTRACTED":
            if target.is_symlink() or not target.is_file():
                raise ExtractionRefusal(f"journaled staging output is missing or unsafe: {member_path}")
            digest, size = sha256_file(target)
            if digest != record.get("sha256") or size != record.get("size_bytes"):
                raise ExtractionRefusal(f"journaled staging output failed hash/size verification: {member_path}")
            expected_files.add(member_path)
        elif record["status"] == "DIRECTORY" and (target.is_symlink() or not target.is_dir()):
            raise ExtractionRefusal(f"journaled staging directory is missing or unsafe: {member_path}")
    if _relative_outputs(stage) != expected_files:
        raise ExtractionRefusal("staging files do not exactly match journaled extraction records")
    return records


def _extract_tree(archive: Path, stage: Path, limits: ExtractLimits, *, start_depth: int = 0) -> list[dict[str, Any]]:
    started = time.monotonic()
    deadline = started + limits.max_wall_seconds
    queue: list[tuple[Path, Path, int, str]] = [(archive, Path("members"), start_depth, archive.name)]
    records_by_path = _load_staging_records(stage)
    all_records = list(records_by_path.values())
    total_budget = [sum(record["size_bytes"] for record in all_records if record.get("status") == "EXTRACTED")]
    processed_archives = 0
    processed_members = 0
    def append_record(row: dict[str, Any]) -> None:
        records_by_path[row["member_path"]] = row
        all_records[:] = list(records_by_path.values())
        _journal_record(stage, row)

    # Re-check the journaled tree against the live source archive before trusting it as resumable.
    for prior in all_records:
        if prior.get("status") == "EXTRACTED" and prior.get("size_bytes", 0) > limits.max_member_bytes:
            raise ExtractionRefusal("journaled staging output exceeds current member limit")
    if total_budget[0] > limits.max_total_bytes:
        raise ExtractionRefusal("journaled staging output exceeds current total-byte limit")
    
    while queue:
        if time.monotonic() > deadline:
            raise ExtractionPaused("recursive archive processing wall-time budget reached")
        nested_source, output_root, depth, parent = queue.pop(0)
        fmt = detect_format(nested_source)
        if fmt not in {"zip", "tar", "gzip", "bzip2", "xz"}:
            append_record({"member_path": parent, "status": "BLOCKED_UNSUPPORTED", "depth": depth,
                           "format": fmt, "reason": "unsupported archive/container format"})
            continue
        if nested_source.stat().st_size > limits.max_input_bytes:
            raise ExtractionRefusal(f"archive input exceeds limit {limits.max_input_bytes}: {parent}")
        processed_archives += 1
        if processed_archives > limits.max_members:
            raise ExtractionRefusal("recursive archive count exceeds configured member limit")
        members = list_members(nested_source, fmt, limits.max_members)
        try:
            processed_members += len(members)
            if processed_members > limits.max_members:
                raise ExtractionRefusal(f"recursive member count exceeds limit {limits.max_members}")
            planned = _validate_members(members, limits)
            for member, rel_name in planned:
                destination_rel = output_root / rel_name
                if len(destination_rel.as_posix()) > limits.max_path_length:
                    raise ExtractionRefusal("recursive output path exceeds configured length")
                member_path = destination_rel.as_posix()
                prior_record = records_by_path.get(member_path)
                if member.kind == "directory":
                    if prior_record is not None and (prior_record.get("status") != "DIRECTORY"
                            or prior_record.get("depth") != depth or prior_record.get("format") != fmt):
                        raise ExtractionRefusal(f"journaled directory does not match source member: {member_path}")
                    (stage / destination_rel).mkdir(parents=True, exist_ok=True)
                    if prior_record is None:
                        append_record({"member_path": member_path, "status": "DIRECTORY",
                                       "depth": depth, "format": fmt})
                    continue
                target = stage / destination_rel
                if prior_record is not None:
                    if (prior_record.get("status") != "EXTRACTED" or prior_record.get("depth") != depth
                            or prior_record.get("format") != fmt or prior_record.get("parent_archive") != parent
                            or (member.size and prior_record.get("size_bytes") != member.size)):
                        raise ExtractionRefusal(f"journaled file does not match source member: {member_path}")
                    # The full source hash is revalidated before recovery and staging bytes are
                    # re-hashed against their durable member records. Do not decompress every
                    # completed source member again: doing so prevents large archives from
                    # advancing within short, lease-safe worker windows.
                    if fmt in {"gzip", "bzip2", "xz"} and prior_record["size_bytes"] / max(member.compressed_size, 1) > limits.max_compression_ratio:
                        raise ExtractionRefusal(f"recovered compression ratio exceeds limit for {member.name!r}")
                    size, digest = prior_record["size_bytes"], prior_record["sha256"]
                else:
                    size, digest = _write_member(member, target, limits, total_budget, deadline)
                    if fmt in {"gzip", "bzip2", "xz"} and size / max(member.compressed_size, 1) > limits.max_compression_ratio:
                        target.unlink(missing_ok=True)
                        raise ExtractionRefusal(f"actual compression ratio exceeds limit for {member.name!r}")
                    member_record = {"member_path": member_path, "status": "EXTRACTED", "depth": depth,
                                     "format": fmt, "size_bytes": size, "sha256": digest, "parent_archive": parent}
                    append_record(member_record)
                    prior_record = member_record
                member_record = prior_record
                nested_fmt = _nested_format(target)
                if nested_fmt not in {"unsupported", "ar-unsupported"}:
                    if depth + 1 > limits.max_depth:
                        member_record["nested_status"] = "BLOCKED_DEPTH"
                        member_record["nested_reason"] = "maximum recursive archive depth exceeded"
                        # Replace the journal entry so durable state includes the depth refusal.
                        with (stage / ".extraction-journal.jsonl").open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps(member_record, sort_keys=True) + "\n")
                            stream.flush()
                            os.fsync(stream.fileno())
                        continue
                    nested_out = destination_rel.with_name(destination_rel.name + ".contents")
                    queue.append((target, nested_out, depth + 1, destination_rel.as_posix()))
        finally:
            _close_member_container(members)

    expected = {row["member_path"] for row in all_records if row["status"] == "EXTRACTED"}
    observed = _relative_outputs(stage)
    if expected != observed:
        raise ExtractionRefusal(f"staging coverage mismatch (expected {len(expected)}, observed {len(observed)})")
    return all_records


def _ensure_schema(db: Path) -> None:
    migration = "corpus-extraction-v6"
    reason = "Recover extraction staging by verified journal records and pause safely within bounded worker time."
    try:
        with connect(db) as con:
            con.executescript(JOB_SCHEMA)
            columns = {row["name"] for row in con.execute("PRAGMA table_info(extraction_jobs)")}
            if "pipeline_version" not in columns:
                con.execute("ALTER TABLE extraction_jobs ADD COLUMN pipeline_version TEXT NOT NULL DEFAULT ''")
            with con:
                con.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version,timestamp,migration,reason,status,error) "
                    "VALUES(?,?,?,?,?,NULL)",
                    (migration, timestamp(), "resumable verified staging and time-budgeted pause", reason, "SUCCESS"),
                )
    except sqlite3.Error as exc:
        try:
            with connect(db) as con:
                con.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations(" 
                    "version TEXT PRIMARY KEY,timestamp TEXT NOT NULL,migration TEXT NOT NULL," 
                    "reason TEXT NOT NULL,status TEXT NOT NULL,error TEXT)"
                )
                with con:
                    con.execute(
                        "INSERT OR REPLACE INTO schema_migrations(version,timestamp,migration,reason,status,error) "
                        "VALUES(?,?,?,?,?,?)",
                        (migration, timestamp(), "resumable verified staging and time-budgeted pause", reason,
                         "FAILED", f"{type(exc).__name__}: {exc}"),
                    )
        except sqlite3.Error:
            pass
        raise


def _file_id(repo_id: str, relative_path: str) -> str:
    return f"{repo_id}:{hashlib.sha256(relative_path.encode()).hexdigest()[:20]}"


def _safe_source(corpus: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or "\\\\" in relative_path:
        raise ValueError("manifest source path is not a canonical relative POSIX path")
    normalized = safe_member_path(relative_path, max_path_length=4096)
    if normalized != relative_path:
        raise ValueError("manifest source path is not canonical")
    source = corpus
    for part in PurePosixPath(normalized).parts:
        source = source / part
        if source.is_symlink():
            raise ValueError("manifest source path contains a symlink")
    resolved = source.resolve(strict=True)
    try:
        resolved.relative_to(corpus)
    except ValueError as exc:
        raise ValueError("manifest source path escapes the raw corpus") from exc
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError("manifest source is not a regular file")
    return resolved


def _ensure_repo_job_schema(db: Path) -> None:
    migration = "corpus-extraction-v3"
    reason = "Persist extraction terminal state and recovery pipeline version in per-repository databases."
    with connect(db) as con:
        con.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY,timestamp TEXT NOT NULL,migration TEXT NOT NULL,reason TEXT NOT NULL,status TEXT NOT NULL,error TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS extraction_jobs(file_id TEXT PRIMARY KEY REFERENCES files(file_id),repository_id TEXT NOT NULL REFERENCES repository(repository_id),source_path TEXT NOT NULL,source_sha256 TEXT NOT NULL,detected_format TEXT NOT NULL,status TEXT NOT NULL,destination TEXT,updated_at TEXT NOT NULL,lease_owner TEXT,lease_expires_at REAL,attempts INTEGER NOT NULL DEFAULT 0,error TEXT,next_action TEXT NOT NULL DEFAULT '',pipeline_version TEXT NOT NULL DEFAULT '')")
        con.execute("CREATE TABLE IF NOT EXISTS processing_errors(error_id INTEGER PRIMARY KEY AUTOINCREMENT,file_id TEXT,phase TEXT NOT NULL,error TEXT NOT NULL,tool TEXT NOT NULL,tool_version TEXT NOT NULL,timestamp TEXT NOT NULL,retry_count INTEGER NOT NULL DEFAULT 0,next_action TEXT NOT NULL)")
        columns = {row["name"] for row in con.execute("PRAGMA table_info(extraction_jobs)")}
        if "pipeline_version" not in columns:
            con.execute("ALTER TABLE extraction_jobs ADD COLUMN pipeline_version TEXT NOT NULL DEFAULT ''")
        with con:
            con.execute("INSERT OR IGNORE INTO schema_migrations(version,timestamp,migration,reason,status,error) VALUES(?,?,?,?,?,NULL)",
                        (migration, timestamp(), "create/extend per-repository extraction_jobs", reason, "SUCCESS"))


def _record_error(db: Path, *, file_id: str, repo_id: str, source_path: str, source_hash: str,
                  fmt: str, owner: str, error: str, next_action: str, attempts: int,
                  status: str = "FAILED", repository_db: Path | None = None) -> None:
    if status not in {"FAILED", "BLOCKED"}:
        raise ValueError(f"invalid terminal extraction status: {status}")
    now = timestamp()
    with connect(db) as con, con:
        con.execute("""INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,
            status,updated_at,lease_owner,lease_expires_at,attempts,error,next_action,pipeline_version)
            VALUES(?,?,?,?,?,?,?,?,NULL,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET status=excluded.status,
            updated_at=excluded.updated_at,lease_owner=NULL,lease_expires_at=NULL,attempts=excluded.attempts,
            error=excluded.error,next_action=excluded.next_action,pipeline_version=excluded.pipeline_version""",
            (file_id, repo_id, source_path, source_hash, fmt, status, now, owner, attempts, error, next_action, PIPELINE_VERSION))
        con.execute("INSERT INTO processing_errors(repository_id,file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?,?)",
                    (repo_id, source_path, "extraction", error, "corpus_extract.py", PIPELINE_VERSION, now, attempts, next_action))
        archive_columns = {row["name"] for row in con.execute("PRAGMA table_info(archives)")}
        if "status" in archive_columns:
            con.execute("UPDATE archives SET status=? WHERE file_id=?", (status, file_id))
        elif "payload_json" in archive_columns:
            con.execute("UPDATE archives SET payload_json=json_set(payload_json,'$.status',?) WHERE file_id=?",
                        (status, file_id))
    if repository_db is None:
        return
    try:
        _ensure_repo_job_schema(repository_db)
        with connect(repository_db) as con, con:
            con.execute("INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,status,destination,updated_at,lease_owner,lease_expires_at,attempts,error,next_action,pipeline_version) VALUES(?,?,?,?,?,?,NULL,?,NULL,NULL,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET status=excluded.status,destination=NULL,updated_at=excluded.updated_at,lease_owner=NULL,lease_expires_at=NULL,attempts=excluded.attempts,error=excluded.error,next_action=excluded.next_action,pipeline_version=excluded.pipeline_version",
                        (file_id, repo_id, source_path, source_hash, fmt, status, now, attempts, error, next_action, PIPELINE_VERSION))
            con.execute("INSERT INTO processing_errors(file_id,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?)",
                        (file_id, "extraction", error, "corpus_extract.py", PIPELINE_VERSION, now, attempts, next_action))
            if status == "BLOCKED":
                con.execute("UPDATE files SET status='BLOCKED' WHERE file_id=?", (file_id,))
            else:
                con.execute("UPDATE files SET status='FAILED' WHERE file_id=?", (file_id,))
            con.execute("DELETE FROM extractions WHERE file_id=?", (file_id,))
            con.execute("INSERT INTO extractions(file_id,status,destination,tool,tool_version,timestamp,error) VALUES(?,?,NULL,?,?,?,?)",
                        (file_id, status, "python-stdlib", PIPELINE_VERSION, now, error))
            archive_columns = {row["name"] for row in con.execute("PRAGMA table_info(archives)")}
            if "status" in archive_columns:
                con.execute("UPDATE archives SET status=? WHERE file_id=?", (status, file_id))
    except (sqlite3.Error, OSError, ValueError) as exc:
        with connect(db) as con, con:
            con.execute("INSERT INTO processing_errors(repository_id,file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?,?)",
                        (repo_id, source_path, "repository-db-mirror", f"{type(exc).__name__}: {exc}",
                         "corpus_extract.py", PIPELINE_VERSION, timestamp(), attempts,
                         "repair per-repository DB schema and reconcile terminal extraction record"))


def _mirror_terminal_state(project: Path, manifest: dict[str, Any], job: dict[str, Any]) -> bool:
    """Idempotently mirror a global FAILED/BLOCKED extraction record into its per-item DB."""
    status = job.get("status")
    if status not in {"FAILED", "BLOCKED"}:
        return False
    repo_id = job["repository_id"]
    repository_db = _repository_db_path(project, manifest, repo_id)
    _ensure_repo_job_schema(repository_db)
    with connect(repository_db) as con:
        prior_job = con.execute("SELECT * FROM extraction_jobs WHERE file_id=?", (job["file_id"],)).fetchone()
        file_row = con.execute("SELECT status FROM files WHERE file_id=?", (job["file_id"],)).fetchone()
        extractions = con.execute("SELECT status,error FROM extractions WHERE file_id=?", (job["file_id"],)).fetchall()
        error_row = con.execute("SELECT 1 FROM processing_errors WHERE file_id=? AND phase='extraction' AND error=? LIMIT 1",
                                (job["file_id"], job["error"] or "")).fetchone()
        archive_columns = {row["name"] for row in con.execute("PRAGMA table_info(archives)")}
        archive_row = (con.execute("SELECT status FROM archives WHERE file_id=?", (job["file_id"],)).fetchone()
                       if "status" in archive_columns else None)
        archive_payload = (con.execute("SELECT payload_json FROM archives WHERE file_id=?", (job["file_id"],)).fetchone()
                           if "payload_json" in archive_columns else None)
        archive_status = (archive_row["status"] if archive_row else
                          (json.loads(archive_payload["payload_json"]).get("status") if archive_payload else None))
        expected_job = (job["status"], job["source_path"], job["source_sha256"], job["detected_format"],
                        job["attempts"], job["error"], job["next_action"],
                        job.get("pipeline_version", PIPELINE_VERSION))
        prior_values = ((prior_job["status"], prior_job["source_path"], prior_job["source_sha256"],
                         prior_job["detected_format"], prior_job["attempts"], prior_job["error"],
                         prior_job["next_action"], prior_job["pipeline_version"])
                        if prior_job else None)
        synchronized = (
            prior_values == expected_job and prior_job["destination"] is None
            and prior_job["lease_owner"] is None and prior_job["lease_expires_at"] is None
            and file_row is not None and file_row["status"] == job["status"]
            and len(extractions) == 1
            and (extractions[0]["status"], extractions[0]["error"]) == (job["status"], job["error"])
            and bool(error_row)
            and ("status" not in archive_columns and "payload_json" not in archive_columns
                 or archive_status == job["status"])
        )
        if synchronized:
            return False
    now = timestamp()
    with connect(repository_db) as con, con:
        con.execute("INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,status,destination,updated_at,lease_owner,lease_expires_at,attempts,error,next_action,pipeline_version) VALUES(?,?,?,?,?,?,NULL,?,NULL,NULL,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET status=excluded.status,destination=NULL,updated_at=excluded.updated_at,lease_owner=NULL,lease_expires_at=NULL,attempts=excluded.attempts,error=excluded.error,next_action=excluded.next_action,pipeline_version=excluded.pipeline_version",
                    (job["file_id"], repo_id, job["source_path"], job["source_sha256"], job["detected_format"],
                     status, now, job["attempts"], job["error"], job["next_action"], job.get("pipeline_version", PIPELINE_VERSION)))
        con.execute("UPDATE files SET status=? WHERE file_id=?", (status, job["file_id"]))
        exists = con.execute("SELECT 1 FROM processing_errors WHERE file_id=? AND phase='extraction' AND error=? LIMIT 1",
                             (job["file_id"], job["error"] or "")).fetchone()
        if not exists:
            con.execute("INSERT INTO processing_errors(file_id,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?)",
                        (job["file_id"], "extraction", job["error"] or status, "corpus_extract.py",
                         job.get("pipeline_version", PIPELINE_VERSION), now, job["attempts"], job["next_action"]))
        con.execute("DELETE FROM extractions WHERE file_id=?", (job["file_id"],))
        con.execute("INSERT INTO extractions(file_id,status,destination,tool,tool_version,timestamp,error) VALUES(?,?,NULL,?,?,?,?)",
                    (job["file_id"], status, "python-stdlib", job.get("pipeline_version", PIPELINE_VERSION),
                     now, job["error"]))
        archive_columns = {row["name"] for row in con.execute("PRAGMA table_info(archives)")}
        if "status" in archive_columns:
            con.execute("UPDATE archives SET status=? WHERE file_id=?", (status, job["file_id"]))
        elif "payload_json" in archive_columns:
            manifest_file_status = None
            for item in manifest.get("files", []):
                if _inventory_file_id(item) == job["file_id"]:
                    manifest_file_status = item.get("status")
                    break
            archive_status = "MISSING" if manifest_file_status == "MISSING" else status
            con.execute("UPDATE archives SET payload_json=json_set(payload_json,'$.status',?) WHERE file_id=?",
                         (archive_status, job["file_id"]))
    return True


def process_file(root: Path, output: Path, manifest: dict[str, Any], row: dict[str, Any], *,
                 limits: ExtractLimits, owner: str, lease_seconds: int = 900) -> dict[str, Any]:
    corpus = root.resolve(strict=True)
    project = output.resolve()
    if project == corpus or corpus in project.parents:
        raise ValueError("generated output may not be inside the raw corpus")
    repo_id = row["repository_id"]
    relative_path = row["original_path"]
    file_id = row["file_id"]
    db_path = project / "data" / "database" / "private_ai_corpus.sqlite"
    manifest = json.loads((project / "data" / "manifests" / "REPO_MANIFEST.json").read_text(encoding="utf-8"))
    _ensure_schema(db_path)
    try:
        repo_database = _repository_db_path(project, manifest, repo_id)
    except (OSError, ValueError, KeyError, sqlite3.Error):
        repo_database = None
    try:
        source = _safe_source(corpus, relative_path)
        actual_source_hash, input_size = sha256_file(source)
    except (OSError, ValueError, ExtractionRefusal) as exc:
        with connect(db_path) as con:
            prior = con.execute("SELECT attempts FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
        attempts = int(prior["attempts"] if prior else 0) + 1
        error = f"{type(exc).__name__}: {exc}"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=row.get("sha256", ""), fmt="source-validation", owner=owner,
                      error=error, next_action="repair manifest/source path and rerun inventory", attempts=attempts,
                      repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}
    now = timestamp()
    with connect(db_path) as con, con:
        con.execute("BEGIN IMMEDIATE")
        prior = con.execute("SELECT * FROM extraction_jobs WHERE file_id=?", (file_id,)).fetchone()
        if (prior and prior["status"] == "VERIFIED" and prior["source_sha256"] == row["sha256"]
                and actual_source_hash == row["sha256"] and prior["destination"]
                and _verified_output_exists(project, db_path, prior)):
            stale_backup = project / prior["destination"]
            stale_backup = stale_backup.parent / f".{stale_backup.name}.previous"
            if stale_backup.exists() and not stale_backup.is_symlink():
                shutil.rmtree(stale_backup)
            return {"file_id": file_id, "repository_id": repo_id, "status": "VERIFIED", "skipped": True}
        if (prior and prior["status"] == "BLOCKED"
                and prior["pipeline_version"] == PIPELINE_VERSION):
            return {"file_id": file_id, "repository_id": repo_id, "status": "BLOCKED", "reason": prior["error"] or "terminal blocked state"}
        if (prior and prior["status"] == "IN_PROGRESS" and prior["lease_expires_at"]
                and prior["lease_expires_at"] > time.time()):
            return {"file_id": file_id, "repository_id": repo_id, "status": "BLOCKED", "reason": "active lease held by another worker"}
        attempts = (0 if prior and prior["pipeline_version"] != PIPELINE_VERSION
                    and prior["status"] in {"FAILED", "BLOCKED"} else int(prior["attempts"] if prior else 0)) + 1
        if (prior and prior["status"] == "FAILED" and prior["pipeline_version"] == PIPELINE_VERSION
                and attempts > limits.max_attempts):
            return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "reason": "retry limit reached", "attempt": attempts - 1}
        con.execute("""INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,status,
            started_at,updated_at,lease_owner,lease_expires_at,attempts,error,next_action,pipeline_version)
            VALUES(?,?,?,?,?,'IN_PROGRESS',?,?,?,?,?,NULL,'extract using configured safety limits',?)
            ON CONFLICT(file_id) DO UPDATE SET source_sha256=excluded.source_sha256,detected_format=excluded.detected_format,
            status='IN_PROGRESS',started_at=excluded.started_at,updated_at=excluded.updated_at,
            lease_owner=excluded.lease_owner,lease_expires_at=excluded.lease_expires_at,
            attempts=excluded.attempts,error=NULL,next_action=excluded.next_action,
            pipeline_version=excluded.pipeline_version""",
            (file_id, repo_id, relative_path, row["sha256"], row["detected_format"], now, now, owner,
             time.time() + lease_seconds, attempts, PIPELINE_VERSION))
    final_hash = actual_source_hash
    if final_hash != row["sha256"]:
        error = "source SHA256 changed since verified inventory"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt="changed", owner=owner, error=error,
                      next_action="rerun inventory; do not extract against stale manifest", attempts=attempts,
                      status="BLOCKED", repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "BLOCKED", "error": error}
    fmt = detect_format(source)
    if fmt not in {"zip", "tar", "gzip", "bzip2", "xz"}:
        reason = f"format {fmt} not supported by extraction pipeline"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt=fmt, owner=owner, error=reason,
                      next_action="use a vetted format-specific parser or retain as blocked", attempts=attempts,
                      status="BLOCKED", repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "BLOCKED", "error": reason}
    if input_size > limits.max_input_bytes:
        reason = f"compressed source size {input_size} exceeds input limit {limits.max_input_bytes}"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt=fmt, owner=owner, error=reason,
                      next_action="process under an explicitly reviewed larger input bound", attempts=attempts,
                      status="BLOCKED", repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "BLOCKED", "error": reason}
    workspace_rel = Path(next((x.get("workspace_path") for x in manifest["repositories"]
                               if x["repository_id"] == repo_id and x.get("workspace_path")), ""))
    if not workspace_rel.parts:
        with connect(db_path) as con:
            stored_workspace = con.execute("SELECT workspace_path FROM repositories WHERE repository_id=?", (repo_id,)).fetchone()
        if not stored_workspace or not stored_workspace["workspace_path"]:
            error = "repository workspace path missing from manifest and global database"
            _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                          source_hash=final_hash, fmt=fmt, owner=owner, error=error,
                          next_action="rebuild/reconcile inventory workspace records", attempts=attempts,
                          repository_db=repo_database)
            return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}
        workspace_rel = Path("data") / "repos" / stored_workspace["workspace_path"]
    if workspace_rel.is_absolute() or ".." in workspace_rel.parts:
        raise ValueError("repository workspace path is not a safe relative path")
    repo = project / workspace_rel
    try:
        repo_resolved = repo.resolve()
        repo_resolved.relative_to(project)
        if repo_resolved == corpus or repo_resolved in corpus.parents or corpus in repo_resolved.parents:
            raise ValueError("manifest workspace overlaps the immutable raw corpus")
        cursor = project
        for part in workspace_rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError("manifest workspace path contains a symlink")
        extracted_root = repo / "extracted"
        if extracted_root.is_symlink():
            raise ValueError("extraction output directory is a symlink")
        extracted_root.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt=fmt, owner=owner, error=error,
                      next_action="repair confined workspace paths and retry", attempts=attempts,
                      repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}
    token = hashlib.sha256(file_id.encode()).hexdigest()[:24]
    final = extracted_root / token
    try:
        if repo_database is None:
            repo_database = _repository_db_path(project, manifest, repo_id)
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        error = f"{type(exc).__name__}: {exc}"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt=fmt, owner=owner, error=error,
                      next_action="reconcile per-repository workspace path/database before extraction", attempts=attempts)
        return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}
    staging = extracted_root / f".{token}.staging"
    backup = extracted_root / f".{token}.previous"
    if any(path.is_symlink() for path in (final, staging, backup)):
        error = "ValueError: extraction destination, staging, or recovery path is a symlink"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt=fmt, owner=owner, error=error,
                      next_action="remove unsafe link after review and restore confined workspace", attempts=attempts,
                      repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}
    if _verify_destination(final, final_hash):
        metadata = json.loads((final / "extraction.json").read_text(encoding="utf-8"))
        try:
            _commit_output_records(db_path, project, final, file_id=file_id, repo_id=repo_id,
                                   source_path=relative_path, source_hash=final_hash, detected_format=fmt,
                                   attempts=attempts, records=metadata.get("files", []),
                                   repository_db=repo_database)
            if backup.exists():
                shutil.rmtree(backup)
            return {"file_id": file_id, "repository_id": repo_id, "status": "VERIFIED",
                    "destination": str(final.relative_to(project)), "files": sum(
                        item.get("status") == "EXTRACTED" for item in metadata.get("files", [])),
                    "bytes": metadata.get("output_bytes", 0), "output_sha256": metadata.get("output_sha256"),
                    "attempt": attempts, "recovered_without_reextracting": True}
        except sqlite3.Error as exc:
            error = f"database recovery failed: {type(exc).__name__}: {exc}"
            _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                          source_hash=final_hash, fmt=fmt, owner=owner, error=error,
                          next_action="repair database and re-index already verified extraction output", attempts=attempts,
                          repository_db=repo_database)
            return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}
    if backup.exists():
        if _verify_destination(final, actual_source_hash):
            if final.exists():
                shutil.rmtree(final)
            os.replace(backup, final)
        else:
            if final.exists():
                shutil.rmtree(final)
            os.replace(backup, final)
    if staging.exists():
        try:
            recovered_records = _load_staging_records(staging)
            recovery = (f"interrupted staging resumed after verifying {sum(record.get('status') == 'EXTRACTED' for record in recovered_records.values())} member output(s)"
                        if recovered_records else "interrupted empty staging resumed")
            recovery_action = "continue extraction from verified journaled outputs"
        except (OSError, ValueError, ExtractionRefusal, json.JSONDecodeError) as exc:
            recovery = f"interrupted staging failed verification and was discarded: {type(exc).__name__}: {exc}"
            recovery_action = "retry extraction from a clean staging directory"
            shutil.rmtree(staging)
        with connect(db_path) as con, con:
            con.execute("INSERT INTO processing_errors(repository_id,file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?,?)",
                        (repo_id, relative_path, "extraction-recovery", recovery, "corpus_extract.py",
                         PIPELINE_VERSION, timestamp(), attempts, recovery_action))
    staging.mkdir(mode=0o700, exist_ok=True)
    published = False
    try:
        records = _extract_tree(source, staging, limits)
        verified_source_hash, verified_source_size = sha256_file(source)
        if verified_source_hash != final_hash or verified_source_size != input_size:
            raise ExtractionRefusal("source changed during extraction; discard output and refresh inventory")
        (staging / ".extraction-journal.jsonl").unlink(missing_ok=True)
        output_digest, output_bytes = digest_tree(staging)
        metadata = {"repository_id": repo_id, "file_id": file_id, "source_path": relative_path,
                    "source_sha256": final_hash, "source_size": input_size, "detected_format": fmt,
                    "limits": asdict(limits), "pipeline_version": PIPELINE_VERSION,
                    "tool": "python-stdlib", "tool_version": sys.version.split()[0],
                    "processed_at": timestamp(), "output_sha256": output_digest,
                    "output_bytes": output_bytes, "files": records}
        (staging / "extraction.json").write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        # Keep any prior destination until the replacement tree is fully staged and verified.
        if final.exists():
            os.replace(final, backup)
        try:
            os.replace(staging, final)
            published = True
        except Exception:
            if backup.exists() and not final.exists():
                os.replace(backup, final)
            raise
        # A crash before the database commit is recoverable from the backup and final path.
        _commit_output_records(db_path, project, final, file_id=file_id, repo_id=repo_id,
                               source_path=relative_path, source_hash=final_hash, detected_format=fmt,
                               attempts=attempts, records=records, repository_db=repo_database)
        if backup.exists():
            shutil.rmtree(backup)
        return {"file_id": file_id, "repository_id": repo_id, "status": "VERIFIED",
                "destination": str(final.relative_to(project)), "files": sum(r["status"] == "EXTRACTED" for r in records),
                "bytes": output_bytes, "output_sha256": output_digest, "attempt": attempts}
    except ExtractionPaused as exc:
        with connect(db_path) as con, con:
            con.execute("UPDATE extraction_jobs SET status='IN_PROGRESS',updated_at=?,lease_owner=NULL,lease_expires_at=0,error=NULL,next_action='resume verified staging on next worker pass' WHERE file_id=?",
                        (timestamp(), file_id))
        return {"file_id": file_id, "repository_id": repo_id, "status": "PAUSED",
                "reason": str(exc), "attempt": attempts}
    except Exception as exc:
        shutil.rmtree(staging, ignore_errors=True)
        if backup.exists() and not final.exists():
            os.replace(backup, final)
        error = f"{type(exc).__name__}: {exc}"
        _record_error(db_path, file_id=file_id, repo_id=repo_id, source_path=relative_path,
                      source_hash=final_hash, fmt=fmt, owner=owner, error=error,
                      next_action="review error and retry with bounded limits or another vetted parser", attempts=attempts,
                      repository_db=repo_database)
        return {"file_id": file_id, "repository_id": repo_id, "status": "FAILED", "error": error, "attempt": attempts}


def digest_tree(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ExtractionRefusal(f"symlink found in extraction output: {path}")
        if not path.is_file() or path.relative_to(root).as_posix() in {"extraction.json", ".extraction-journal.jsonl"}:
            continue
        rel = path.relative_to(root).as_posix().encode()
        content_hash, size = sha256_file(path)
        digest.update(len(rel).to_bytes(8, "big"))
        digest.update(rel)
        digest.update(bytes.fromhex(content_hash))
        total += size
    return digest.hexdigest(), total


def _verify_destination(destination: Path, source_hash: str) -> bool:
    try:
        if destination.is_symlink() or not destination.is_dir():
            return False
        metadata_path = destination / "extraction.json"
        if metadata_path.is_symlink() or not metadata_path.is_file():
            return False
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        # v5 changed terminal-state reconciliation, not the extraction format or output bytes.
        # Continue validating existing v4 trees by their source and deterministic content digest.
        if (metadata.get("pipeline_version") not in {PIPELINE_VERSION, "safe-extract-v5", "safe-extract-v4"}
                or metadata.get("source_sha256") != source_hash
                or metadata.get("output_sha256") is None):
            return False
        digest, size = digest_tree(destination)
        return digest == metadata["output_sha256"] and size == metadata.get("output_bytes")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, ExtractionRefusal):
        return False


def _inventory_file_id(row: dict[str, Any]) -> str:
    return row.get("file_id") or _file_id(row["repository_id"], row["relative_path"])


def _ensure_repo_schema(db: Path) -> None:
    migration = "corpus-extraction-v1"
    schema = """
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version TEXT PRIMARY KEY, timestamp TEXT NOT NULL, migration TEXT NOT NULL,
      reason TEXT NOT NULL, status TEXT NOT NULL, error TEXT
    );
    CREATE TABLE IF NOT EXISTS extraction_jobs (
      file_id TEXT PRIMARY KEY REFERENCES files(file_id), repository_id TEXT NOT NULL REFERENCES repository(repository_id),
      source_path TEXT NOT NULL, source_sha256 TEXT NOT NULL, detected_format TEXT NOT NULL,
      status TEXT NOT NULL, destination TEXT, updated_at TEXT NOT NULL, lease_owner TEXT,
      lease_expires_at REAL, attempts INTEGER NOT NULL DEFAULT 0, error TEXT, next_action TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS extraction_outputs (
      extracted_file_id TEXT PRIMARY KEY, source_file_id TEXT NOT NULL REFERENCES files(file_id),
      repository_id TEXT NOT NULL REFERENCES repository(repository_id), member_path TEXT NOT NULL,
      extracted_path TEXT NOT NULL, parent_archive TEXT NOT NULL, depth INTEGER NOT NULL,
      size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, detected_format TEXT NOT NULL,
      status TEXT NOT NULL, tool TEXT NOT NULL, tool_version TEXT NOT NULL, processed_at TEXT NOT NULL,
      UNIQUE(source_file_id,extracted_path)
    );
    """
    try:
        with connect(db) as con:
            con.executescript(schema)
            with con:
                con.execute("INSERT OR IGNORE INTO schema_migrations(version,timestamp,migration,reason,status,error) VALUES(?,?,?,?,?,NULL)",
                            (migration, timestamp(), "create repository extraction_jobs and extraction_outputs",
                             "Mirror global extraction state and member provenance in the per-repository database.", "SUCCESS"))
    except sqlite3.Error as exc:
        try:
            with connect(db) as con:
                con.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY,timestamp TEXT NOT NULL,migration TEXT NOT NULL,reason TEXT NOT NULL,status TEXT NOT NULL,error TEXT)")
                with con:
                    con.execute("INSERT OR REPLACE INTO schema_migrations(version,timestamp,migration,reason,status,error) VALUES(?,?,?,?,?,?)",
                                (migration, timestamp(), "create repository extraction_jobs and extraction_outputs",
                                 "Mirror global extraction state and member provenance in the per-repository database.",
                                 "FAILED", f"{type(exc).__name__}: {exc}"))
        except sqlite3.Error:
            pass
        raise


def _repository_db_path(project: Path, manifest: dict[str, Any], repo_id: str) -> Path:
    repository = next(item for item in manifest["repositories"] if item["repository_id"] == repo_id)
    workspace_path = repository.get("workspace_path")
    if not workspace_path:
        with connect(project / "data" / "database" / "private_ai_corpus.sqlite") as con:
            stored = con.execute("SELECT workspace_path FROM repositories WHERE repository_id=?", (repo_id,)).fetchone()
        if not stored or not stored["workspace_path"]:
            raise FileNotFoundError(f"workspace path is missing for {repo_id}")
        workspace_path = str(Path("data") / "repos" / stored["workspace_path"])
    workspace_rel = Path(workspace_path)
    if workspace_rel.is_absolute() or ".." in workspace_rel.parts:
        raise ValueError("manifest repository workspace path is not a safe relative path")
    workspace = project / workspace_rel
    resolved_workspace = workspace.resolve(strict=True)
    resolved_workspace.relative_to(project)
    if resolved_workspace == project or project not in resolved_workspace.parents:
        raise ValueError("per-repository workspace is not confined under project output")
    for current, _, _ in os.walk(resolved_workspace, followlinks=False):
        if Path(current).is_symlink():
            raise ValueError("per-repository workspace contains a symlinked directory")
    candidates = list((resolved_workspace / "db").glob("*.sqlite"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"expected exactly one per-repository SQLite database for {repo_id}; found {len(candidates)}")
    database = candidates[0]
    if database.is_symlink():
        raise ValueError("per-repository database is a symlink")
    return database


def _commit_output_records(db: Path, project: Path, final: Path, *, file_id: str,
                           repo_id: str, source_path: str, source_hash: str, detected_format: str,
                           attempts: int, records: list[dict[str, Any]],
                           repository_db: Path | None = None) -> None:
    if repository_db is not None:
        _ensure_repo_schema(repository_db)
        with connect(repository_db) as repo_con, repo_con:
            repo_con.execute("INSERT OR REPLACE INTO file_hashes(file_id,sha256,size_bytes) SELECT file_id,sha256,size_bytes FROM files WHERE file_id=? AND sha256 IS NOT NULL", (file_id,))
            repo_con.execute("DELETE FROM extraction_outputs WHERE source_file_id=?", (file_id,))
            repo_con.execute("DELETE FROM extraction_jobs WHERE file_id=?", (file_id,))
            repo_con.execute("INSERT INTO extraction_jobs(file_id,repository_id,source_path,source_sha256,detected_format,status,destination,updated_at,attempts,next_action) VALUES(?,?,?,?,?,'VERIFIED',?,?,?,'parse extracted files')",
                             (file_id, repo_id, source_path, source_hash, detected_format,
                              str(final.relative_to(project)), timestamp(), attempts))
            repo_con.execute("DELETE FROM extractions WHERE file_id=?", (file_id,))
            repo_con.execute("INSERT INTO extractions(file_id,status,destination,tool,tool_version,timestamp,error) VALUES(?,?,?,?,?,?,NULL)",
                             (file_id, "VERIFIED", str(final.relative_to(project)), "python-stdlib", sys.version.split()[0], timestamp()))
            for record in records:
                if record.get("status") != "EXTRACTED":
                    continue
                out_file_id = hashlib.sha256(f"{file_id}:{record['member_path']}".encode()).hexdigest()
                extracted_path = str((final / record["member_path"]).relative_to(project))
                repo_con.execute("INSERT INTO extraction_outputs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (out_file_id, file_id, repo_id, record["member_path"], extracted_path, source_path,
                                  record["depth"], record["size_bytes"], record["sha256"], record["format"],
                                  "EXTRACTED", "python-stdlib", sys.version.split()[0], timestamp()))
                repo_con.execute("INSERT OR REPLACE INTO provenance(record_id,file_id,tool,tool_version,pipeline,timestamp,source_path,source_sha256,details_json) VALUES(?,?,?,?,?,?,?,?,?)",
                                 (out_file_id, file_id, "corpus_extract.py", sys.version.split()[0], PIPELINE_VERSION,
                                  timestamp(), source_path, source_hash,
                                  json.dumps({"member_path": record["member_path"], "member_sha256": record["sha256"],
                                              "depth": record["depth"], "format": record["format"]}, sort_keys=True)))
            archive_columns = {row["name"] for row in repo_con.execute("PRAGMA table_info(archives)")}
            if "status" in archive_columns:
                repo_con.execute("UPDATE archives SET status='EXTRACTED' WHERE file_id=?", (file_id,))
    with connect(db) as con, con:
        con.execute("DELETE FROM extraction_outputs WHERE source_file_id=?", (file_id,))
        con.execute("DELETE FROM extracted_files WHERE file_id=?", (file_id,))
        for record in records:
            if record.get("status") != "EXTRACTED":
                continue
            out_file_id = hashlib.sha256(f"{file_id}:{record['member_path']}".encode()).hexdigest()
            extracted_path = str((final / record["member_path"]).relative_to(project))
            con.execute("INSERT INTO extraction_outputs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (out_file_id, file_id, repo_id, record["member_path"], extracted_path, source_path,
                         record["depth"], record["size_bytes"], record["sha256"], record["format"],
                         "EXTRACTED", "python-stdlib", sys.version.split()[0], timestamp()))
            con.execute("""INSERT INTO extracted_files(record_id,repository_id,file_id,entity_key,payload_json,source_path,confidence,created_at)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (out_file_id, repo_id, file_id, record["member_path"], json.dumps(record, sort_keys=True),
                         extracted_path, "HIGH", timestamp()))
        con.execute("UPDATE extraction_jobs SET status='VERIFIED',destination=?,updated_at=?,lease_owner=NULL,lease_expires_at=NULL,error=NULL,next_action='parse extracted files' WHERE file_id=?",
                    (str(final.relative_to(project)), timestamp(), file_id))
        archive_columns = {row["name"] for row in con.execute("PRAGMA table_info(archives)")}
        if "status" in archive_columns:
            con.execute("UPDATE archives SET status='EXTRACTED' WHERE file_id=?", (file_id,))
        elif "payload_json" in archive_columns:
            con.execute("UPDATE archives SET payload_json=json_set(payload_json,'$.status','EXTRACTED') WHERE file_id=?", (file_id,))


def _verified_output_exists(project: Path, db: Path, row: sqlite3.Row) -> bool:
    destination = row["destination"]
    if not destination or not _verify_destination(project / destination, row["source_sha256"]):
        return False
    try:
        metadata = json.loads((project / destination / "extraction.json").read_text(encoding="utf-8"))
        expected = {
            hashlib.sha256(f"{row['file_id']}:{entry['member_path']}".encode()).hexdigest(): entry
            for entry in metadata.get("files", []) if entry.get("status") == "EXTRACTED"
        }
        with connect(db) as con:
            actual = {item["extracted_file_id"]: item for item in con.execute(
                "SELECT extracted_file_id,member_path,extracted_path,size_bytes,sha256,status "
                "FROM extraction_outputs WHERE source_file_id=?", (row["file_id"],))}
        if set(expected) != set(actual):
            return False
        for record_id, entry in expected.items():
            item = actual[record_id]
            expected_path = str((project / destination / entry["member_path"]).relative_to(project))
            if (item["member_path"] != entry["member_path"] or item["extracted_path"] != expected_path
                    or item["size_bytes"] != entry["size_bytes"] or item["sha256"] != entry["sha256"]
                    or item["status"] != "EXTRACTED"):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, json.JSONDecodeError):
        return False


def run(root: Path, output: Path, *, repo_id: str | None = None, limit: int = 10,
        owner: str = "local-worker", lease_seconds: int = 900, limits: ExtractLimits | None = None) -> dict[str, Any]:
    limits = limits or ExtractLimits()
    limits.validate()
    corpus = root.resolve(strict=True)
    project = output.resolve()
    if project == corpus or corpus in project.parents:
        raise ValueError("generated output may not be inside the raw corpus")
    manifest = json.loads((project / "data" / "manifests" / "REPO_MANIFEST.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    if limit < 1:
        raise ValueError("limit must be positive")
    all_candidates = [row for row in files if row["node_type"] == "file" and row["archive_status"] == "candidate-not-expanded"]
    if repo_id:
        all_candidates = [row for row in all_candidates if row["repository_id"] == repo_id]
    db_path = project / "data" / "database" / "private_ai_corpus.sqlite"
    if not db_path.is_file():
        raise FileNotFoundError(f"global corpus database is missing: {db_path}")
    _ensure_schema(db_path)
    with connect(db_path) as con:
        jobs = {row["file_id"]: dict(row) for row in con.execute(
            "SELECT file_id,repository_id,source_path,detected_format,status,attempts,lease_expires_at,destination,source_sha256,error,next_action,pipeline_version "
            "FROM extraction_jobs")}
        # Leave old terminal rows intact until the scheduler has mirrored them into the
        # per-repository DB. process_file resets the retry count only when it claims the job.
    results: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    terminal_mirrored = 0
    for row in all_candidates:
        normalized = {**row, "file_id": _inventory_file_id(row)}
        job = jobs.get(normalized["file_id"])
        if job and job["status"] in {"FAILED", "BLOCKED"}:
            try:
                if _mirror_terminal_state(project, manifest, job):
                    terminal_mirrored += 1
            except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
                with connect(db_path) as con, con:
                    con.execute("INSERT INTO processing_errors(repository_id,file_path,phase,error,tool,tool_version,timestamp,retry_count,next_action) VALUES(?,?,?,?,?,?,?,?,?)",
                                (job["repository_id"], job["source_path"], "repository-db-mirror",
                                 f"{type(exc).__name__}: {exc}", "corpus_extract.py", PIPELINE_VERSION,
                                 timestamp(), job["attempts"], "repair per-repository DB and retry terminal-state reconciliation"))
        if job and job["status"] == "VERIFIED" and _verified_output_exists(project, db_path, job):
            destination = project / job["destination"]
            backup = destination.parent / f".{destination.name}.previous"
            if backup.exists() and not backup.is_symlink():
                shutil.rmtree(backup)
            results.append({"file_id": normalized["file_id"], "repository_id": normalized["repository_id"],
                            "status": "VERIFIED", "skipped": True})
            continue
        if (job and job["status"] == "BLOCKED"
                and job["pipeline_version"] == PIPELINE_VERSION):
            results.append({"file_id": normalized["file_id"], "repository_id": normalized["repository_id"],
                            "status": "BLOCKED", "reason": job["error"] or "terminal blocked state"})
            continue
        if job and job["status"] == "IN_PROGRESS" and job["lease_expires_at"] and job["lease_expires_at"] > time.time():
            results.append({"file_id": normalized["file_id"], "repository_id": normalized["repository_id"],
                            "status": "BLOCKED", "reason": "active lease held by another worker"})
            continue
        if (job and job["status"] == "FAILED" and job["pipeline_version"] == PIPELINE_VERSION
                and job["attempts"] >= limits.max_attempts):
            results.append({"file_id": normalized["file_id"], "repository_id": normalized["repository_id"],
                            "status": "FAILED", "reason": "retry limit reached", "attempt": job["attempts"]})
            continue
        pending.append(normalized)
        if len(pending) >= limit:
            break
    for normalized in pending:
        try:
            result = process_file(root, output, manifest, normalized, limits=limits,
                                  owner=owner, lease_seconds=lease_seconds)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            try:
                with connect(db_path) as con:
                    prior = con.execute("SELECT attempts FROM extraction_jobs WHERE file_id=?", (normalized["file_id"],)).fetchone()
                attempt = int(prior["attempts"] if prior else 0) + 1
                try:
                    repository_db = _repository_db_path(project, manifest, normalized["repository_id"])
                except (OSError, ValueError, KeyError, sqlite3.Error):
                    repository_db = None
                _record_error(db_path, file_id=normalized["file_id"], repo_id=normalized["repository_id"],
                              source_path=normalized["original_path"], source_hash=normalized.get("sha256", ""),
                              fmt=normalized.get("detected_format", "unknown"), owner=owner,
                              error=error, next_action="inspect worker/database failure and retry", attempts=attempt,
                              repository_db=repository_db)
            except sqlite3.Error:
                pass
            result = {"file_id": normalized["file_id"], "repository_id": normalized["repository_id"],
                      "status": "FAILED", "error": error}
        results.append(result)
    return {"total_candidates_in_batch": len(pending), "terminal_records_mirrored": terminal_mirrored,
            "verified": sum(x["status"] == "VERIFIED" and not x.get("skipped") for x in results),
            "skipped_verified": sum(x.get("skipped", False) for x in results),
            "blocked": sum(x["status"] == "BLOCKED" for x in results),
            "failed": sum(x["status"] == "FAILED" for x in results),
            "paused": sum(x["status"] == "PAUSED" for x in results), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("repo"))
    parser.add_argument("--output", type=Path, default=Path("."))
    parser.add_argument("--repo-id", help="limit processing to one stable repository ID")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--owner", default=f"pid-{os.getpid()}")
    parser.add_argument("--max-input-mb", type=int, default=512)
    parser.add_argument("--max-members", type=int, default=10_000)
    parser.add_argument("--max-member-mb", type=int, default=32)
    parser.add_argument("--max-total-mb", type=int, default=256)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--max-ratio", type=float, default=200.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--max-wall-seconds", type=int, default=75)
    parser.add_argument("--min-free-mb", type=int, default=256)
    args = parser.parse_args()
    try:
        limits = ExtractLimits(max_input_bytes=args.max_input_mb * 1024 * 1024,
                               max_members=args.max_members,
                               max_member_bytes=args.max_member_mb * 1024 * 1024,
                               max_total_bytes=args.max_total_mb * 1024 * 1024,
                               max_compression_ratio=args.max_ratio,
                               max_depth=args.max_depth,
                               max_wall_seconds=args.max_wall_seconds,
                               max_attempts=args.max_attempts,
                               min_free_bytes=args.min_free_mb * 1024 * 1024)
        if args.lease_seconds < 1:
            raise ValueError("lease-seconds must be positive")
        result = run(args.root, args.output, repo_id=args.repo_id, limit=args.limit,
                     owner=args.owner, lease_seconds=args.lease_seconds, limits=limits)
    except Exception as exc:
        print(f"extraction worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
