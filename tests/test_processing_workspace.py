"""Tests for SSD processing workspace configuration and quota checks."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts.processing_workspace import HARD_CAP_BYTES, initialize_workspace, measure_usage


class ProcessingWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_env = {name: os.environ.get(name) for name in ("TMPDIR", "TEMP", "TMP", "SQLITE_TMPDIR")}
        self.original_tempdir = tempfile.tempdir
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.scratch = self.root / "scratch"
        self.project.mkdir()
        self.scratch.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()
        tempfile.tempdir = self.original_tempdir
        for name, value in self.original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_initializes_temp_subdirs_and_verifies_real_write(self) -> None:
        result = initialize_workspace(self.scratch, project=self.project, require_separate_device=False)
        self.assertTrue(result["probe_verified"])
        self.assertEqual(result["python_tempdir"], result["directories"]["tmp"])
        self.assertEqual(result["tmpdir"], result["directories"]["tmp"])
        self.assertEqual(result["sqlite_tmpdir"], result["directories"]["tmp"])
        self.assertTrue(all(Path(path).is_dir() for path in result["directories"].values()))
        self.assertEqual(measure_usage(self.scratch), 0)

    def test_enforces_20_gib_absolute_cap(self) -> None:
        with self.assertRaisesRegex(ValueError, "within 20 GiB"):
            initialize_workspace(self.scratch, project=self.project,
                                 cap_bytes=HARD_CAP_BYTES + 1, require_separate_device=False)

    def test_rejects_processing_root_inside_project(self) -> None:
        nested = self.project / "scratch"
        with self.assertRaisesRegex(ValueError, "inside the durable project root"):
            initialize_workspace(nested, project=self.project, require_separate_device=False)

    def test_rejects_symlink_in_usage_walk(self) -> None:
        (self.scratch / "safe").write_bytes(b"ok")
        (self.scratch / "linked").symlink_to(self.scratch / "safe")
        with self.assertRaisesRegex(ValueError, "symlink"):
            measure_usage(self.scratch)


if __name__ == "__main__":
    unittest.main()
