#!/usr/bin/env python3
"""Configure and account for bounded Private AI processing scratch space."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path("/home/chris/data-processing")
HARD_CAP_BYTES = 20 * 1024**3
WARNING_BYTES = 19 * 1024**3
EMERGENCY_BYTES = 19_500 * 1024**2
SCRATCH_DIRS = ("tmp", "work", "cache", "extract", "scratch", "staging", "logs", "index")


def measure_usage(root: Path) -> int:
    """Return logical bytes in scratch files; reject symlinks and special files."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"processing root is missing, symlinked, or not a directory: {root}")
    total = 0
    for base, directories, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in directories:
            item = base_path / name
            if item.is_symlink() or not item.is_dir():
                raise ValueError(f"unsafe processing directory: {item}")
        for name in files:
            item = base_path / name
            if item.is_symlink():
                raise ValueError(f"symlink in processing workspace: {item}")
            info = item.stat(follow_symlinks=False)
            if not item.is_file() or info.st_size < 0:
                raise ValueError(f"non-regular file in processing workspace: {item}")
            total += info.st_size
    return total


def check_capacity(root: Path, *, additional_bytes: int = 0, cap_bytes: int = HARD_CAP_BYTES) -> dict[str, int | str]:
    if additional_bytes < 0 or cap_bytes < 1 or cap_bytes > HARD_CAP_BYTES:
        raise ValueError("additional bytes must be non-negative and cap must be within 20 GiB")
    used = measure_usage(root)
    projected = used + additional_bytes
    free = shutil.disk_usage(root).free
    if projected > cap_bytes:
        raise ValueError(f"processing workspace cap exceeded: used={used}, additional={additional_bytes}, cap={cap_bytes}")
    if additional_bytes > free:
        raise ValueError(f"processing filesystem lacks space: free={free}, additional={additional_bytes}")
    severity = ("EMERGENCY" if projected >= EMERGENCY_BYTES else
                "WARNING" if projected >= WARNING_BYTES else "NORMAL")
    return {"used_bytes": used, "additional_bytes": additional_bytes, "projected_bytes": projected,
            "free_bytes": free, "cap_bytes": cap_bytes, "severity": severity}


def initialize_workspace(
    root: Path = DEFAULT_ROOT,
    *,
    project: Path | None = None,
    cap_bytes: int = HARD_CAP_BYTES,
    require_separate_device: bool = True,
) -> dict[str, Any]:
    """Create SSD scratch subdirectories, route Python/SQLite temp use, and verify a write."""
    root = Path(root).expanduser()
    if root.is_symlink():
        raise ValueError(f"processing root must not be a symlink: {root}")
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    if project is not None:
        project = Path(project).resolve(strict=True)
        if root == project or project in root.parents:
            raise ValueError("processing workspace must not be inside the durable project root")
        same_device = root.stat().st_dev == project.stat().st_dev
        if require_separate_device and same_device:
            raise ValueError("processing workspace and durable project root are on the same filesystem device")
    else:
        same_device = False

    private_root = root / "private-ai-tmp"
    if not private_root.exists() and measure_usage(root) > cap_bytes:
        raise ValueError(f"processing workspace already exceeds cap before initialization: cap={cap_bytes}")
    if not private_root.exists() and shutil.disk_usage(root).free < 8 * 1024**2:
        raise ValueError("processing filesystem has insufficient space to initialize scratch directories")
    if private_root.is_symlink():
        raise ValueError(f"processing directory must not be a symlink: {private_root}")
    private_root.mkdir(exist_ok=True)
    directories: dict[str, str] = {}
    for name in SCRATCH_DIRS:
        path = private_root / name
        if path.is_symlink():
            raise ValueError(f"processing directory must not be a symlink: {path}")
        path.mkdir(exist_ok=True)
        if not path.is_dir():
            raise ValueError(f"processing path is not a directory: {path}")
        directories[name] = str(path)

    capacity = check_capacity(root, cap_bytes=cap_bytes)
    os.environ["TMPDIR"] = directories["tmp"]
    os.environ["TEMP"] = directories["tmp"]
    os.environ["TMP"] = directories["tmp"]
    os.environ["SQLITE_TMPDIR"] = directories["tmp"]
    tempfile.tempdir = None
    python_tempdir = tempfile.gettempdir()

    fd, probe_name = tempfile.mkstemp(prefix="private-ai-ssd-probe-", dir=directories["tmp"])
    probe = Path(probe_name)
    expected = b"private-ai-processing-write-probe\n"
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
        probe_bytes = probe.read_bytes()
        probe_device = probe.stat().st_dev
        if probe_bytes != expected or probe_device != root.stat().st_dev:
            raise OSError("temporary write probe did not verify on the configured processing filesystem")
    finally:
        probe.unlink(missing_ok=True)

    capacity = check_capacity(root, cap_bytes=cap_bytes)
    return {
        "root": str(root),
        "directories": directories,
        "python_tempdir": python_tempdir,
        "tmpdir": os.environ["TMPDIR"],
        "sqlite_tmpdir": os.environ["SQLITE_TMPDIR"],
        "root_device": root.stat().st_dev,
        "project_device": project.stat().st_dev if project is not None else None,
        "same_device_as_project": same_device,
        "probe_device": probe_device,
        "probe_verified": True,
        **capacity,
    }
