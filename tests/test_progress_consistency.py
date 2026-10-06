"""Tests for the control-plane consistency guard (internal sum and live database)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.progress_consistency import (
    DEFAULT_DB,
    PARSER_VERSION,
    find_breakdown_issues,
    find_database_issues,
    iter_breakdowns,
    load_database_counts,
    scan,
)
from scripts.progress_consistency import default_paths

# Counts whose sum (84,968) is one tranche larger than the stated total (83,968); this reproduces
# the historical drift the guard exists to catch.
DRIFTED_LINE = (
    "Direct SQL: **83,968** rows for `stdlib-text-v3`: **69,061 PARSED**, **9,942 SENSITIVE**, "
    "**3,587 UNSUPPORTED_TYPE**, **2,178 BINARY**, **178 TOO_LARGE**, **22 UNSUPPORTED_ENCODING**."
)
CONSISTENT_LINE = DRIFTED_LINE.replace("83,968", "84,968")
# A small self-consistent breakdown used for database tests (total 18).
LIVE_COUNTS = {"PARSED": 10, "SENSITIVE": 3, "UNSUPPORTED_TYPE": 2, "BINARY": 1,
               "UNSUPPORTED_ENCODING": 1, "TOO_LARGE": 1}
LIVE_LINE = ("Rows: **18** for stdlib-text-v3: 10 PARSED, 3 SENSITIVE, 2 UNSUPPORTED_TYPE, "
             "1 BINARY, 1 UNSUPPORTED_ENCODING, 1 TOO_LARGE.")


def _breakdown_issues(text: str) -> list[dict[str, object]]:
    return find_breakdown_issues(iter_breakdowns(text))


class BreakdownConsistencyTests(unittest.TestCase):
    def test_consistent_breakdown_passes(self) -> None:
        self.assertEqual(_breakdown_issues(CONSISTENT_LINE), [])

    def test_breakdown_sum_not_matching_stated_total_is_reported(self) -> None:
        issues = _breakdown_issues(DRIFTED_LINE)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["kind"], "breakdown-sum")
        self.assertEqual(issues[0]["computed_total"], 84_968)
        self.assertEqual(issues[0]["line"], 1)
        self.assertIn(83_968, issues[0]["numbers_on_line"])

    def test_off_by_one_total_is_reported(self) -> None:
        issues = _breakdown_issues(CONSISTENT_LINE.replace("84,968", "84,969"))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["computed_total"], 84_968)

    def test_batch_composition_without_total_keyword_is_ignored(self) -> None:
        text = "Newest tranche: 850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE."
        self.assertEqual(_breakdown_issues(text), [])

    def test_fewer_than_five_statuses_is_ignored(self) -> None:
        self.assertEqual(_breakdown_issues("Rows 3: 2 PARSED, 1 BINARY."), [])


class DatabaseComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _make_db(self, counts: dict[str, int]) -> Path:
        path = self.root / "corpus.sqlite"
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE parsed_content(status TEXT, parser_version TEXT)")
        for status, count in counts.items():
            con.executemany("INSERT INTO parsed_content(status,parser_version) VALUES(?,?)",
                            [(status, PARSER_VERSION)] * count)
        con.commit()
        con.close()
        return path

    def test_load_database_counts_aggregates_by_status(self) -> None:
        db = load_database_counts(self._make_db(LIVE_COUNTS), PARSER_VERSION)
        self.assertEqual(db["total"], 18)
        self.assertEqual(db["statuses"], LIVE_COUNTS)

    def test_missing_database_is_none(self) -> None:
        self.assertIsNone(load_database_counts(self.root / "absent.sqlite", PARSER_VERSION))

    def test_matching_breakdown_passes(self) -> None:
        records = iter_breakdowns(LIVE_LINE)
        db = load_database_counts(self._make_db(LIVE_COUNTS), PARSER_VERSION)
        self.assertEqual(find_database_issues(records, db, PARSER_VERSION), [])

    def test_stale_document_total_is_reported(self) -> None:
        records = iter_breakdowns(LIVE_LINE)
        db = load_database_counts(self._make_db({**LIVE_COUNTS, "BINARY": 2}), PARSER_VERSION)
        issues = find_database_issues(records, db, PARSER_VERSION)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["kind"], "database-total")
        self.assertEqual(issues[0]["documented_total"], 18)
        self.assertEqual(issues[0]["database_total"], 19)

    def test_mismatched_status_with_equal_total_is_reported(self) -> None:
        # PARSED +1 and SENSITIVE -1 keep the sum at 18 while disagreeing with the database.
        line = ("Rows: **18**: 11 PARSED, 2 SENSITIVE, 2 UNSUPPORTED_TYPE, 1 BINARY, "
                "1 UNSUPPORTED_ENCODING, 1 TOO_LARGE.")
        records = iter_breakdowns(line)
        db = load_database_counts(self._make_db(LIVE_COUNTS), PARSER_VERSION)
        issues = find_database_issues(records, db, PARSER_VERSION)
        self.assertEqual({issue["status"] for issue in issues}, {"PARSED", "SENSITIVE"})
        self.assertTrue(all(issue["kind"] == "database-status" for issue in issues))

    def test_historical_smaller_totals_are_not_compared(self) -> None:
        older = ("Rows: **6** for stdlib-text-v3: 3 PARSED, 1 SENSITIVE, 1 UNSUPPORTED_TYPE, "
                 "1 BINARY, 0 UNSUPPORTED_ENCODING, 0 TOO_LARGE.")
        records = iter_breakdowns(f"{older}\n{LIVE_LINE}")
        db = load_database_counts(self._make_db(LIVE_COUNTS), PARSER_VERSION)
        self.assertEqual(find_database_issues(records, db, PARSER_VERSION), [])


class ControlPlaneIntegrationTests(unittest.TestCase):
    def test_control_plane_documents_are_self_consistent(self) -> None:
        paths = default_paths(Path(__file__).resolve().parents[1])
        if not paths:
            self.skipTest("no control-plane documents available")
        report = scan(paths, database=None)
        self.assertEqual(report["issue_count"], 0, report["issues"])

    def test_control_plane_documents_match_live_database(self) -> None:
        project = Path(__file__).resolve().parents[1]
        paths = default_paths(project)
        if not paths:
            self.skipTest("no control-plane documents available")
        database = load_database_counts(project / DEFAULT_DB, PARSER_VERSION)
        if database is None:
            self.skipTest("live corpus database unavailable")
        report = scan(paths, database=database)
        self.assertEqual(report["issue_count"], 0, report["issues"])


if __name__ == "__main__":
    unittest.main()
